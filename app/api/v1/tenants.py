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
from .auth_multi_tenant import require_super_admin, get_current_active_user
from ...utils.tenant_utils import create_tenant_slug, validate_tenant_domain

router = APIRouter(prefix="/tenants", tags=["Tenant Management"])

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
        max_organizations=tenant_data.max_organizations or 50,
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
    
    # Get total user count across all organizations
    user_count = db.query(User).join(Organization).filter(
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
        max_organizations=tenant.max_organizations,
        created_at=tenant.created_at
    )
