from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid
from datetime import datetime

from ...core.database import get_db, Tenant, Organization, User
from ...schemas.schemas import (
    TenantCreate, TenantUpdate, TenantResponse, 
    TenantListResponse, TenantStatsResponse
)
from .auth_multi_tenant import get_current_active_user
from .auth_admin import require_super_admin
from ...utils.tenant_utils import create_tenant_slug, validate_tenant_domain

router = APIRouter(tags=["Tenant Management"])

@router.post("", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Create a new enterprise tenant (Super Admin only)."""
    
    # Validate tenant domain if provided
    if tenant_data.domain:
        if not validate_tenant_domain(tenant_data.domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        # Check if domain already exists
        existing_domain = db.query(Tenant).filter(Tenant.domain == tenant_data.domain).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain already registered"
            )
    
    # Create tenant slug
    tenant_slug = create_tenant_slug(tenant_data.name)
    
    # Check if slug already exists
    existing_slug = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if existing_slug:
        # Add random suffix to make it unique
        import random
        tenant_slug = f"{tenant_slug}-{random.randint(1000, 9999)}"
    
    # Create new tenant
    new_tenant = Tenant(
        id=uuid.uuid4(),
        name=tenant_data.name,
        slug=tenant_slug,
        domain=tenant_data.domain,
        description=tenant_data.description,
        logo_url=tenant_data.logo_url,
        is_active=True,
        created_by=current_user.id,
        created_at=datetime.utcnow()
    )
    
    db.add(new_tenant)
    db.commit()
    db.refresh(new_tenant)
    
    return TenantResponse.from_orm(new_tenant)

@router.get("", response_model=TenantListResponse)
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """List all tenants with optional filtering (Super Admin only)."""
    
    query = db.query(Tenant)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Tenant.name.ilike(f"%{search}%"),
                Tenant.domain.ilike(f"%{search}%"),
                Tenant.description.ilike(f"%{search}%")
            )
        )
    
    if is_active is not None:
        query = query.filter(Tenant.is_active == is_active)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply pagination
    tenants = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit).all()
    
    return TenantListResponse(
        tenants=[TenantResponse.from_orm(tenant) for tenant in tenants],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get tenant details (Super Admin only)."""
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    return TenantResponse.from_orm(tenant)

@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_update: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Update tenant information (Super Admin only)."""
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Update fields if provided
    update_data = tenant_update.dict(exclude_unset=True)
    
    # Validate domain if being updated
    if "domain" in update_data and update_data["domain"]:
        if not validate_tenant_domain(update_data["domain"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        # Check if domain already exists (excluding current tenant)
        existing_domain = db.query(Tenant).filter(
            and_(Tenant.domain == update_data["domain"], Tenant.id != tenant_id)
        ).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain already registered"
            )
    
    # Apply updates
    for field, value in update_data.items():
        setattr(tenant, field, value)
    
    tenant.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(tenant)
    
    return TenantResponse.from_orm(tenant)

@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: str,
    force: bool = Query(False, description="Force delete even if tenant has organizations"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Delete a tenant (Super Admin only)."""
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Check if tenant has organizations
    org_count = db.query(Organization).filter(Organization.tenant_id == tenant_id).count()
    
    if org_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant has {org_count} organizations. Use force=true to delete anyway."
        )
    
    if force and org_count > 0:
        # Delete all organizations under this tenant
        # This will cascade delete users and predictions
        organizations = db.query(Organization).filter(Organization.tenant_id == tenant_id).all()
        for org in organizations:
            db.delete(org)
    
    # Delete the tenant
    db.delete(tenant)
    db.commit()
    
    return {"message": f"Tenant '{tenant.name}' deleted successfully"}

@router.get("/{tenant_id}/stats", response_model=TenantStatsResponse)
async def get_tenant_stats(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get tenant statistics (Super Admin only)."""
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get organization count
    org_count = db.query(Organization).filter(Organization.tenant_id == tenant_id).count()
    
    # Get total user count across all organizations (fix ambiguous join)
    user_count = db.query(User).join(
        Organization, User.organization_id == Organization.id
    ).filter(
        Organization.tenant_id == tenant_id
    ).count()
    
    # Get active organization count
    active_org_count = db.query(Organization).filter(
        and_(Organization.tenant_id == tenant_id, Organization.is_active == True)
    ).count()
    
    return TenantStatsResponse(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        total_organizations=org_count,
        active_organizations=active_org_count,
        total_users=user_count,
        created_at=tenant.created_at
    )

@router.post("/{tenant_id}/assign-admin", response_model=dict)
async def assign_tenant_admin(
    tenant_id: str,
    request_data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Assign a user as tenant admin (Super Admin only)."""
    
    user_email = request_data.get("user_email")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_email is required"
        )
    
    # Validate tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Find user by email
    user = db.query(User).filter(User.email == user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is already a tenant admin for a different tenant
    if user.global_role == "tenant_admin" and user.tenant_id and str(user.tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a tenant admin for another tenant"
        )
    
    # Assign tenant admin role
    user.global_role = "tenant_admin"
    user.tenant_id = tenant_id
    user.organization_id = None  # Remove from specific org if assigned
    user.organization_role = None
    
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"Successfully assigned {user.email} as tenant admin for {tenant.name}",
        "user_id": str(user.id),
        "tenant_id": tenant_id,
        "role": user.global_role
    }

@router.delete("/{tenant_id}/remove-admin/{user_id}", response_model=dict)
async def remove_tenant_admin(
    tenant_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Remove tenant admin role from a user (Super Admin only)."""
    
    # Validate tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Find user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is tenant admin for this tenant
    if user.global_role != "tenant_admin" or str(user.tenant_id) != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a tenant admin for this tenant"
        )
    
    # Remove tenant admin role
    user.global_role = "user"
    user.tenant_id = None
    
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"Successfully removed tenant admin role from {user.email}",
        "user_id": str(user.id),
        "new_role": user.global_role
    }

@router.get("/{tenant_id}/admins", response_model=List[dict])
async def get_tenant_admins(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get list of tenant admins for a specific tenant (Super Admin only)."""
    
    # Validate tenant exists
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Get all tenant admins for this tenant
    tenant_admins = db.query(User).filter(
        and_(
            User.global_role == "tenant_admin",
            User.tenant_id == tenant_id
        )
    ).all()
    
    return [
        {
            "user_id": str(admin.id),
            "email": admin.email,
            "full_name": admin.full_name,
            "username": admin.username,
            "is_active": admin.is_active,
            "created_at": admin.created_at
        }
        for admin in tenant_admins
    ]
