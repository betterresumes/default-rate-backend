from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid
import logging
from datetime import datetime

from ...core.database import (
    get_db, Organization, User, Tenant, OrganizationMemberWhitelist,
    Company, AnnualPrediction, QuarterlyPrediction
)
from ...schemas.schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    OrganizationListResponse, OrganizationDetailedResponse, OrgAdminInfo,
    WhitelistCreate, WhitelistResponse,
    WhitelistListResponse, UserResponse, UserListResponse,
    EnhancedOrganizationResponse, EnhancedOrganizationListResponse,
    EnhancedTenantInfo, OrganizationMemberInfo
)
from .auth_multi_tenant import get_current_active_user
from .auth_admin import (
    require_super_admin, require_tenant_admin_or_above, require_org_admin_or_above
)
from ...middleware.rate_limiting import (
    rate_limit_org_create, rate_limit_org_read, rate_limit_org_update, 
    rate_limit_org_delete, rate_limit_org_token, rate_limit_api
)
from ...utils.tenant_utils import (
    create_organization_slug, generate_join_token, 
    validate_organization_domain, is_email_whitelisted
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Organization Management"])

@router.post("", response_model=OrganizationResponse)
@rate_limit_org_create
async def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new organization."""
    
    if current_user.role == "super_admin":
        tenant_id = org_data.tenant_id
    elif current_user.role == "tenant_admin":
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant admin must belong to a tenant"
            )
        tenant_id = current_user.tenant_id
        if org_data.tenant_id and str(org_data.tenant_id) != str(tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create organization for different tenant"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or tenant admin can create organizations"
        )
    
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
    
    if org_data.domain:
        if not validate_organization_domain(org_data.domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        existing_domain = db.query(Organization).filter(Organization.domain == org_data.domain).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain already registered"
            )
    
    org_slug = create_organization_slug(org_data.name)
    
    existing_slug = db.query(Organization).filter(Organization.slug == org_slug).first()
    if existing_slug:
        import random
        org_slug = f"{org_slug}-{random.randint(1000, 9999)}"
    
    join_token = generate_join_token()
    
    new_organization = Organization(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=org_data.name,
        slug=org_slug,
        domain=org_data.domain,
        description=org_data.description,
        logo_url=org_data.logo_url,
        join_token=join_token,
        join_enabled=True,
        default_role=org_data.default_role or "org_member",
        max_users=org_data.max_users or 500,
        is_active=True,
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        join_created_at=datetime.utcnow()
    )
    
    db.add(new_organization)
    db.commit()
    db.refresh(new_organization)
    
    return OrganizationResponse.from_orm(new_organization)

@router.get("/", response_model=EnhancedOrganizationListResponse)
@rate_limit_org_read
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in name, domain, or description"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID (Super Admin only)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    List organizations with role-based access control and pagination.
    
    - **Super Admin**: Can see all organizations, optionally filter by tenant
    - **Tenant Admin**: Can see only their tenant's organizations
    - **Org Admin/Member**: Can see only their own organization
    """
    try:
        skip = (page - 1) * limit
        
        query = db.query(Organization)
        
        if current_user.role == "super_admin":
            if tenant_id:
                query = query.filter(Organization.tenant_id == tenant_id)
        elif current_user.role == "tenant_admin":
            if not current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Tenant admin must belong to a tenant"
                )
            query = query.filter(Organization.tenant_id == current_user.tenant_id)
        else:
            if not current_user.organization_id:
                return OrganizationListResponse(organizations=[], total=0, skip=skip, limit=limit)
            query = query.filter(Organization.id == current_user.organization_id)
        
        if search:
            query = query.filter(
                or_(
                    Organization.name.ilike(f"%{search}%"),
                    Organization.domain.ilike(f"%{search}%"),
                    Organization.description.ilike(f"%{search}%")
                )
            )
        
        if is_active is not None:
            query = query.filter(Organization.is_active == is_active)
        
        total = query.count()
        
        organizations = query.order_by(Organization.created_at.desc()).offset(skip).limit(limit).all()
        
        enhanced_organizations = []
        total_admins = 0
        total_members = 0
        total_users = 0
        
        for org in organizations:
            try:
                tenant_info = None
                if org.tenant_id:
                    tenant = db.query(Tenant).filter(Tenant.id == org.tenant_id).first()
                    if tenant:
                        tenant_admins = db.query(User).filter(
                            and_(User.tenant_id == org.tenant_id, User.role == "tenant_admin")
                        ).all()
                        
                        tenant_admin_info = [
                            OrganizationMemberInfo(
                                id=str(admin.id),
                                tenant_id=str(admin.tenant_id) if admin.tenant_id else None,
                                organization_id=str(admin.organization_id) if admin.organization_id else None,
                                email=admin.email,
                                username=admin.username,
                                full_name=admin.full_name,
                                role=admin.role,
                                is_active=admin.is_active,
                                created_at=admin.created_at
                            ) for admin in tenant_admins
                        ]
                        
                        tenant_info = EnhancedTenantInfo(
                            id=str(tenant.id),
                            name=tenant.name,
                            description=tenant.description,
                            tenant_code=tenant.slug,  
                            logo_url=tenant.logo_url,
                            is_active=tenant.is_active,
                            created_at=tenant.created_at,
                            tenant_admins=tenant_admin_info,
                            total_tenant_admins=len(tenant_admin_info)
                        )
                
                org_admin = db.query(User).filter(
                    and_(User.organization_id == org.id, User.role == "org_admin")
                ).first()
                
                org_admin_info = None
                if org_admin:
                    org_admin_info = OrganizationMemberInfo(
                        id=str(org_admin.id),
                        tenant_id=str(org_admin.tenant_id) if org_admin.tenant_id else None,
                        organization_id=str(org_admin.organization_id) if org_admin.organization_id else None,
                        email=org_admin.email,
                        username=org_admin.username,
                        full_name=org_admin.full_name,
                        role=org_admin.role,
                        is_active=org_admin.is_active,
                        created_at=org_admin.created_at
                    )
                
                org_members = db.query(User).filter(
                    and_(User.organization_id == org.id, User.role == "org_member")
                ).all()
                
                member_info = [
                    OrganizationMemberInfo(
                        id=str(member.id),
                        tenant_id=str(member.tenant_id) if member.tenant_id else None,
                        organization_id=str(member.organization_id) if member.organization_id else None,
                        email=member.email,
                        username=member.username,
                        full_name=member.full_name,
                        role=member.role,
                        is_active=member.is_active,
                        created_at=member.created_at
                    ) for member in org_members
                ]
                
                org_total_users = len(org_members) + (1 if org_admin else 0)
                org_active_users = len([m for m in org_members if m.is_active]) + (1 if org_admin and org_admin.is_active else 0)
                org_total_members = len(org_members)
                org_active_members = len([m for m in org_members if m.is_active])
                
                enhanced_org = EnhancedOrganizationResponse(
                    id=str(org.id),
                    tenant_id=str(org.tenant_id) if org.tenant_id else None,
                    name=org.name,
                    slug=org.slug,
                    domain=org.domain,
                    description=org.description,
                    logo_url=org.logo_url,
                    max_users=org.max_users,
                    join_token=org.join_token,
                    join_enabled=org.join_enabled,
                    default_role=org.default_role,
                    is_active=org.is_active,
                    created_by=str(org.created_by),
                    created_at=org.created_at,
                    updated_at=org.updated_at,
                    join_created_at=org.join_created_at,
                    tenant=tenant_info,
                    org_admin=org_admin_info,
                    members=member_info,
                    total_users=org_total_users,
                    active_users=org_active_users,
                    total_members=org_total_members,
                    active_members=org_active_members
                )
                
                enhanced_organizations.append(enhanced_org)
                
                if org_admin:
                    total_admins += 1
                total_members += org_total_members
                total_users += org_total_users
                
            except Exception as e:
                logger.error(f"Error building enhanced response for organization {org.id}: {str(e)}")
                continue
        
        return EnhancedOrganizationListResponse(
            organizations=enhanced_organizations,
            total=total,
            skip=skip,
            limit=limit,
            total_admins=total_admins,
            total_members=total_members,
            total_users=total_users
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in list_organizations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving organizations. Please try again later."
        )

@router.get("/{org_id}", response_model=EnhancedOrganizationResponse)
@rate_limit_org_read
async def get_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get organization details with tenant, admin, and member information."""
    try:
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        if current_user.role == "super_admin":
            pass
        elif current_user.role == "tenant_admin":
            if organization.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
        else:
            if str(organization.id) != str(current_user.organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
        
        tenant_info = None
        if organization.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == organization.tenant_id).first()
            if tenant:
                tenant_admins = db.query(User).filter(
                    and_(User.tenant_id == organization.tenant_id, User.role == "tenant_admin")
                ).all()
                
                tenant_admin_info = [
                    OrganizationMemberInfo(
                        id=str(admin.id),
                        tenant_id=str(admin.tenant_id) if admin.tenant_id else None,
                        organization_id=str(admin.organization_id) if admin.organization_id else None,
                        email=admin.email,
                        username=admin.username,
                        full_name=admin.full_name,
                        role=admin.role,
                        is_active=admin.is_active,
                        created_at=admin.created_at
                    ) for admin in tenant_admins
                ]
                
                tenant_info = EnhancedTenantInfo(
                    id=str(tenant.id),
                    name=tenant.name,
                    description=tenant.description,
                    tenant_code=tenant.slug,  # Use slug as tenant_code
                    logo_url=tenant.logo_url,
                    is_active=tenant.is_active,
                    created_at=tenant.created_at,
                    tenant_admins=tenant_admin_info,
                    total_tenant_admins=len(tenant_admin_info)
                )
        
        org_admin = db.query(User).filter(
            and_(User.organization_id == organization.id, User.role == "org_admin")
        ).first()
        
        org_admin_info = None
        if org_admin:
            org_admin_info = OrganizationMemberInfo(
                id=str(org_admin.id),
                tenant_id=str(org_admin.tenant_id) if org_admin.tenant_id else None,
                organization_id=str(org_admin.organization_id) if org_admin.organization_id else None,
                email=org_admin.email,
                username=org_admin.username,
                full_name=org_admin.full_name,
                role=org_admin.role,
                is_active=org_admin.is_active,
                created_at=org_admin.created_at
            )
        
        org_members = db.query(User).filter(
            and_(User.organization_id == organization.id, User.role == "org_member")
        ).all()
        
        member_info = [
            OrganizationMemberInfo(
                id=str(member.id),
                tenant_id=str(member.tenant_id) if member.tenant_id else None,
                organization_id=str(member.organization_id) if member.organization_id else None,
                email=member.email,
                username=member.username,
                full_name=member.full_name,
                role=member.role,
                is_active=member.is_active,
                created_at=member.created_at
            ) for member in org_members
        ]
        
        org_total_users = len(org_members) + (1 if org_admin else 0)
        org_active_users = len([m for m in org_members if m.is_active]) + (1 if org_admin and org_admin.is_active else 0)
        org_total_members = len(org_members)
        org_active_members = len([m for m in org_members if m.is_active])
        
        enhanced_org = EnhancedOrganizationResponse(
            id=str(organization.id),
            tenant_id=str(organization.tenant_id) if organization.tenant_id else None,
            name=organization.name,
            slug=organization.slug,
            domain=organization.domain,
            description=organization.description,
            logo_url=organization.logo_url,
            max_users=organization.max_users,
            join_token=organization.join_token,
            join_enabled=organization.join_enabled,
            default_role=organization.default_role,
            is_active=organization.is_active,
            created_by=str(organization.created_by),
            created_at=organization.created_at,
            updated_at=organization.updated_at,
            join_created_at=organization.join_created_at,
            tenant=tenant_info,
            org_admin=org_admin_info,
            members=member_info,
            total_users=org_total_users,
            active_users=org_active_users,
            total_members=org_total_members,
            active_members=org_active_members
        )
        
        return enhanced_org
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving organization details"
        )

@router.put("/{org_id}", response_model=OrganizationResponse)
@rate_limit_org_update
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
    
    if (current_user.role not in ["super_admin", "tenant_admin"] and
        (str(current_user.organization_id) != org_id or current_user.role != "org_admin")):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to update organization"
        )
    
    if (current_user.role == "tenant_admin" and 
        organization.tenant_id != current_user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot update organization from different tenant"
        )
    
    update_data = org_update.dict(exclude_unset=True)
    
    if "domain" in update_data and update_data["domain"]:
        if not validate_organization_domain(update_data["domain"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
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
@rate_limit_org_delete
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
    
    if current_user.role not in ["super_admin", "tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or tenant admin can delete organizations"
        )
    
    if (current_user.role == "tenant_admin" and 
        organization.tenant_id != current_user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete organization from different tenant"
        )
    
    user_count = db.query(User).filter(User.organization_id == org_id).count()
    
    if user_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization has {user_count} users. Use force=true to delete anyway."
        )
    
    if force and user_count > 0:
        users = db.query(User).filter(User.organization_id == org_id).all()
        for user in users:
            user.organization_id = None
    
    db.delete(organization)
    db.commit()
    
    return {"message": f"Organization '{organization.name}' deleted successfully"}

@router.post("/{org_id}/regenerate-token")
@rate_limit_org_token
async def regenerate_join_token(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin_or_above)
):
    """Regenerate organization join token."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if (current_user.role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
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


@router.get("/{org_id}/whitelist", response_model=WhitelistListResponse)
@rate_limit_org_read
async def get_organization_whitelist(
    org_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin_or_above)
):
    """Get organization whitelist (Org Admin only)."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if (current_user.role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
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
@rate_limit_org_update
async def add_to_whitelist(
    org_id: str,
    whitelist_data: WhitelistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin_or_above)
):
    """Add email to organization whitelist."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if (current_user.role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
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
@rate_limit_org_update
async def remove_from_whitelist(
    org_id: str,
    email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_org_admin_or_above)
):
    """Remove email from organization whitelist."""
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if (current_user.role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
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


@router.get("/{org_id}/users", response_model=UserListResponse)
@rate_limit_org_read
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
    
    if (current_user.role not in ["super_admin", "tenant_admin"] and
        str(current_user.organization_id) != org_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this organization"
        )
    
    query = db.query(User).filter(User.organization_id == org_id)
    
    if role:
        query = query.filter(User.role == role)
    
    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{org_id}/details", response_model=OrganizationDetailedResponse)
@rate_limit_org_read
async def get_organization_details(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get detailed organization information including org admins.
    
    Returns:
    - Basic organization information
    - List of organization administrators
    - User statistics (total users, active users)
    """
    try:
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        if current_user.role == "super_admin":
            pass
        elif current_user.role == "tenant_admin":
            if organization.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
        else:
            if str(organization.id) != str(current_user.organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
        
        org_admins = db.query(User).filter(
            and_(
                User.organization_id == organization.id,
                User.role == "org_admin",
                User.is_active == True
            )
        ).all()
        
        total_users = db.query(User).filter(User.organization_id == organization.id).count()
        active_users = db.query(User).filter(
            and_(
                User.organization_id == organization.id,
                User.is_active == True
            )
        ).count()
        
        org_admin_info = []
        for admin in org_admins:
            try:
                admin_info = OrgAdminInfo(
                    user_id=str(admin.id),
                    email=admin.email,
                    full_name=admin.full_name,
                    username=admin.username,
                    is_active=admin.is_active,
                    assigned_at=admin.updated_at or admin.created_at
                )
                org_admin_info.append(admin_info)
            except Exception as e:
                logger.error(f"Error converting admin {admin.id} to response: {str(e)}")
                continue
        
        org_dict = {
            "id": str(organization.id),
            "tenant_id": str(organization.tenant_id) if organization.tenant_id else None,
            "name": organization.name,
            "slug": organization.slug,
            "domain": organization.domain,
            "description": organization.description,
            "logo_url": organization.logo_url,
            "max_users": organization.max_users,
            "join_token": organization.join_token,
            "join_enabled": organization.join_enabled,
            "default_role": organization.default_role,
            "is_active": organization.is_active,
            "created_by": str(organization.created_by),
            "created_at": organization.created_at,
            "updated_at": organization.updated_at,
            "join_created_at": organization.join_created_at,
            "org_admins": org_admin_info,
            "total_users": total_users,
            "active_users": active_users
        }
        
        return OrganizationDetailedResponse(**org_dict)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving organization details"
        )

@router.get("/{org_id}/admins", response_model=List[OrgAdminInfo])
@rate_limit_org_read
async def get_organization_admins(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get list of organization administrators.
    
    Returns list of users with 'org_admin' role in the organization.
    """
    try:
        organization = db.query(Organization).filter(Organization.id == org_id).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        if current_user.role == "super_admin":
            pass
        elif current_user.role == "tenant_admin":
            if organization.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
        else:
            if str(organization.id) != str(current_user.organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this organization"
                )
        
        org_admins = db.query(User).filter(
            and_(
                User.organization_id == organization.id,
                User.role == "org_admin"
            )
        ).all()
        
        admin_responses = []
        for admin in org_admins:
            try:
                admin_info = OrgAdminInfo(
                    user_id=str(admin.id),
                    email=admin.email,
                    full_name=admin.full_name,
                    username=admin.username,
                    is_active=admin.is_active,
                    assigned_at=admin.updated_at or admin.created_at
                )
                admin_responses.append(admin_info)
            except Exception as e:
                logger.error(f"Error converting admin {admin.id} to response: {str(e)}")
                continue
        
        return admin_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting organization admins: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving organization administrators"
        )


@router.patch("/{org_id}/global-data-access")
@rate_limit_org_update
async def update_global_data_access(
    org_id: str,
    allow_access: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update global data access setting for an organization.
    
    This endpoint controls whether organization users can see global predictions 
    and companies created by super_admin users.
    
    **Access Control:**
    - **Super Admin**: Can update any organization's global data access
    - **Tenant Admin**: Can update organizations within their tenant
    - **Org Admin**: Cannot update this setting (security restriction)
    
    **Parameters:**
    - org_id: Organization ID to update
    - allow_access: True to allow access to global data, False to restrict to org data only
    """
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if current_user.role == "super_admin":
        pass
    elif current_user.role == "tenant_admin":
        if organization.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update global data access for organization from different tenant"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges. Only super_admin or tenant_admin can update global data access settings"
        )
    
    try:
        organization.allow_global_data_access = allow_access
        db.commit()
        db.refresh(organization)
        
        access_status = "enabled" if allow_access else "disabled"
        
        return {
            "success": True,
            "message": f"Global data access {access_status} for organization '{organization.name}'",
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "allow_global_data_access": organization.allow_global_data_access
            },
            "impact": {
                "description": f"Organization users can {'now access' if allow_access else 'no longer access'} global predictions and companies",
                "affected_data": [
                    "Global predictions created by super_admin users",
                    "Global companies accessible across organizations"
                ],
                "security_note": "This setting only affects data visibility, not data modification permissions"
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating global data access for org {org_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating global data access setting"
        )

@router.get("/{org_id}/global-data-access")
@rate_limit_org_read
async def get_global_data_access_status(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get the current global data access setting for an organization.
    
    **Access Control:**
    - **Super Admin**: Can view any organization's setting
    - **Tenant Admin**: Can view organizations within their tenant  
    - **Org Admin**: Can view their own organization's setting
    - **Org Members**: Can view their own organization's setting
    """
    
    organization = db.query(Organization).filter(Organization.id == org_id).first()
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if current_user.role == "super_admin":
        pass
    elif current_user.role == "tenant_admin":
        if organization.tenant_id != current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot view global data access setting for organization from different tenant"
            )
    elif str(current_user.organization_id) == org_id:
        pass
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to view this organization's global data access setting"
        )
    
    try:
        return {
            "success": True,
            "organization": {
                "id": str(organization.id),
                "name": organization.name,
                "allow_global_data_access": organization.allow_global_data_access
            },
            "explanation": {
                "current_setting": "enabled" if organization.allow_global_data_access else "disabled",
                "meaning": (
                    "Organization users can access global predictions and companies" 
                    if organization.allow_global_data_access 
                    else "Organization users can only access their organization's data"
                ),
                "global_data_includes": [
                    "Predictions created by super_admin users",
                    "Companies marked as global (is_global=true)",
                    "Cross-organization benchmark data"
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting global data access status for org {org_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving global data access setting"
        )
