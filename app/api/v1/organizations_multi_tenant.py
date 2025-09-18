from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid
from datetime import datetime

from ...core.database import (
    get_db, Organization, User, Tenant, OrganizationMemberWhitelist,
    Company, AnnualPrediction, QuarterlyPrediction
)
from ...schemas.schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationListResponse, WhitelistCreate, WhitelistResponse,
    WhitelistListResponse, UserResponse, UserListResponse
)
from .auth_multi_tenant import (
    require_super_admin, require_tenant_admin, require_org_admin,
    get_current_active_user
)
from ...utils.tenant_utils import (
    create_organization_slug, generate_join_token, 
    validate_organization_domain, is_email_whitelisted
)

router = APIRouter(prefix="/organizations", tags=["Organization Management"])

@router.post("", response_model=OrganizationResponse)
async def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new organization."""
    
    # Determine who can create organizations
    if current_user.global_role == "super_admin":
        # Super admin can create orgs for any tenant or as standalone
        tenant_id = org_data.tenant_id
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can only create orgs within their tenant
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant admin must belong to a tenant"
            )
        tenant_id = current_user.tenant_id
        if org_data.tenant_id and org_data.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create organization for different tenant"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or tenant admin can create organizations"
        )
    
    # Validate tenant if provided
    if tenant_id:
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tenant not found"
            )
        
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot create organization for inactive tenant"
            )
        
        # Check tenant organization limit
        org_count = db.query(Organization).filter(Organization.tenant_id == tenant_id).count()
        if tenant.max_organizations and org_count >= tenant.max_organizations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tenant has reached maximum organizations limit ({tenant.max_organizations})"
            )
    
    # Validate domain if provided
    if org_data.domain:
        if not validate_organization_domain(org_data.domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        # Check if domain already exists
        existing_domain = db.query(Organization).filter(Organization.domain == org_data.domain).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain already registered"
            )
    
    # Create organization slug
    org_slug = create_organization_slug(org_data.name)
    
    # Ensure slug is unique
    existing_slug = db.query(Organization).filter(Organization.slug == org_slug).first()
    if existing_slug:
        import random
        org_slug = f"{org_slug}-{random.randint(1000, 9999)}"
    
    # Generate join token
    join_token = generate_join_token()
    
    # Create new organization
    new_organization = Organization(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=org_data.name,
        slug=org_slug,
        domain=org_data.domain,
        description=org_data.description,
        logo_url=org_data.logo_url,
        max_users=org_data.max_users or 100,
        join_token=join_token,
        join_enabled=True,
        default_role=org_data.default_role or "user",
        is_active=True,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        join_created_at=datetime.utcnow()
    )
    
    db.add(new_organization)
    db.commit()
    db.refresh(new_organization)
    
    return OrganizationResponse.from_orm(new_organization)

@router.get("", response_model=OrganizationListResponse)
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List organizations based on user role and permissions."""
    
    query = db.query(Organization)
    
    # Apply role-based filtering
    if current_user.global_role == "super_admin":
        # Super admin can see all organizations
        if tenant_id:
            query = query.filter(Organization.tenant_id == tenant_id)
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can only see their tenant's organizations
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant admin must belong to a tenant"
            )
        query = query.filter(Organization.tenant_id == current_user.tenant_id)
    else:
        # Regular users can only see their own organization
        if not current_user.organization_id:
            return OrganizationListResponse(organizations=[], total=0, skip=skip, limit=limit)
        query = query.filter(Organization.id == current_user.organization_id)
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Organization.name.ilike(f"%{search}%"),
                Organization.domain.ilike(f"%{search}%"),
                Organization.description.ilike(f"%{search}%")
            )
        )
    
    # Apply active filter
    if is_active is not None:
        query = query.filter(Organization.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    organizations = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()
    
    return OrganizationListResponse(
        organizations=[OrganizationResponse.from_orm(org) for org in organizations],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get organization details."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check access permissions
    if current_user.global_role == "super_admin":
        # Super admin can access any organization
        pass
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can access organizations in their tenant
        if organization.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
    else:
        # Regular users can only access their own organization
        if str(organization.id) != str(current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
    
    return OrganizationResponse.from_orm(organization)

@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    org_update: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update organization information."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check permissions - only org admin, tenant admin, or super admin
    if (current_user.global_role not in ["super_admin", "tenant_admin"] and
        (str(current_user.organization_id) != org_id or current_user.organization_role != "admin")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to update organization"
        )
    
    # If tenant admin, ensure it's their tenant's organization
    if (current_user.global_role == "tenant_admin" and 
        organization.tenant_id != current_user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update organization from different tenant"
        )
    
    # Apply updates
    update_data = org_update.dict(exclude_unset=True)
    
    # Validate domain if being updated
    if "domain" in update_data and update_data["domain"]:
        if not validate_organization_domain(update_data["domain"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        # Check if domain already exists (excluding current org)
        existing_domain = db.query(Organization).filter(
            and_(Organization.domain == update_data["domain"], Organization.id != org_id)
        ).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain already registered"
            )
    
    for field, value in update_data.items():
        setattr(organization, field, value)
    
    organization.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(organization)
    
    return OrganizationResponse.from_orm(organization)

@router.delete("/{org_id}")
async def delete_organization(
    org_id: str,
    force: bool = Query(False, description="Force delete even if organization has users"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete an organization."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Only super admin or tenant admin can delete organizations
    if current_user.global_role not in ["super_admin", "tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or tenant admin can delete organizations"
        )
    
    # If tenant admin, ensure it's their tenant's organization
    if (current_user.global_role == "tenant_admin" and 
        organization.tenant_id != current_user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete organization from different tenant"
        )
    
    # Check if organization has users
    user_count = db.query(User).filter(User.organization_id == org_id).count()
    
    if user_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization has {user_count} users. Use force=true to delete anyway."
        )
    
    if force and user_count > 0:
        # Remove users from organization (don't delete user accounts)
        users = db.query(User).filter(User.organization_id == org_id).all()
        for user in users:
            user.organization_id = None
            user.organization_role = "user"
    
    # Delete organization (this will cascade delete whitelist entries)
    db.delete(organization)
    db.commit()
    
    return {"message": f"Organization '{organization.name}' deleted successfully"}

@router.post("/{org_id}/regenerate-token")
async def regenerate_join_token(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin)
):
    """Regenerate organization join token."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check if user has permission to regenerate token
    if (current_user.global_role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # Generate new token
    new_token = generate_join_token()
    organization.join_token = new_token
    organization.join_created_at = datetime.utcnow()
    organization.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "message": "Join token regenerated successfully",
        "new_token": new_token,
        "join_url": f"/join/{new_token}"
    }

# Whitelist management endpoints

@router.get("/{org_id}/whitelist", response_model=WhitelistListResponse)
async def get_organization_whitelist(
    org_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin)
):
    """Get organization whitelist (Org Admin only)."""
    
    # Verify access to organization
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if (current_user.global_role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # Get whitelist entries
    query = db.query(OrganizationMemberWhitelist).filter(
        OrganizationMemberWhitelist.organization_id == org_id
    )
    
    total = query.count()
    whitelist_entries = query.order_by(OrganizationMemberWhitelist.added_at.desc()).offset(skip).limit(limit).all()
    
    return WhitelistListResponse(
        whitelist=[WhitelistResponse.from_orm(entry) for entry in whitelist_entries],
        total=total,
        skip=skip,
        limit=limit
    )

@router.post("/{org_id}/whitelist", response_model=WhitelistResponse)
async def add_to_whitelist(
    org_id: str,
    whitelist_data: WhitelistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin)
):
    """Add email to organization whitelist."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if (current_user.global_role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # Check if email already whitelisted
    existing_entry = db.query(OrganizationMemberWhitelist).filter(
        and_(
            OrganizationMemberWhitelist.organization_id == org_id,
            OrganizationMemberWhitelist.email == whitelist_data.email.lower()
        )
    ).first()
    
    if existing_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already whitelisted"
        )
    
    # Add to whitelist
    new_entry = OrganizationMemberWhitelist(
        id=uuid.uuid4(),
        organization_id=uuid.UUID(org_id),
        email=whitelist_data.email.lower(),
        added_by=current_user.id,
        added_at=datetime.utcnow(),
        status="active"
    )
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    
    return WhitelistResponse.from_orm(new_entry)

@router.delete("/{org_id}/whitelist/{email}")
async def remove_from_whitelist(
    org_id: str,
    email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin)
):
    """Remove email from organization whitelist."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if (current_user.global_role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # Find whitelist entry
    whitelist_entry = db.query(OrganizationMemberWhitelist).filter(
        and_(
            OrganizationMemberWhitelist.organization_id == org_id,
            OrganizationMemberWhitelist.email == email.lower()
        )
    ).first()
    
    if not whitelist_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found in whitelist"
        )
    
    db.delete(whitelist_entry)
    db.commit()
    
    return {"message": f"Email {email} removed from whitelist"}

# Organization users management

@router.get("/{org_id}/users", response_model=UserListResponse)
async def get_organization_users(
    org_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get organization users."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Check access permissions
    if (current_user.global_role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    # Query users
    query = db.query(User).filter(User.organization_id == org_id)
    
    if role:
        query = query.filter(User.organization_role == role)
    
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        skip=skip,
        limit=limit
    )
