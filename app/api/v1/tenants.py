from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid
from datetime import datetime

from ...core.database import get_db, Tenant, Organization, User
from ...schemas.schemas import (
    TenantCreate, TenantUpdate, TenantResponse, 
    TenantListResponse, TenantStatsResponse,
    ComprehensiveTenantListResponse, ComprehensiveTenantResponse,
    TenantAdminInfo, DetailedOrganizationInfo, OrganizationAdminInfo, OrganizationUserInfo
)
from .auth_multi_tenant import get_current_active_user
from .auth_admin import require_super_admin, require_tenant_admin_or_above
from ...utils.tenant_utils import create_tenant_slug, validate_tenant_domain

router = APIRouter(tags=["Tenant Management"])

@router.post("", response_model=TenantResponse)
async def create_tenant(
    tenant_data: TenantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Create a new enterprise tenant (Super Admin only)."""
    
    if tenant_data.domain:
        if not validate_tenant_domain(tenant_data.domain):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        existing_domain = db.query(Tenant).filter(Tenant.domain == tenant_data.domain).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain already registered"
            )
    
    tenant_slug = create_tenant_slug(tenant_data.name)
    
    existing_slug = db.query(Tenant).filter(Tenant.slug == tenant_slug).first()
    if existing_slug:
        import random
        tenant_slug = f"{tenant_slug}-{random.randint(1000, 9999)}"
    
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

@router.get("", response_model=ComprehensiveTenantListResponse)
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above)
):
    """List tenants with comprehensive details - Super Admin sees all, Tenant Admin sees only their tenant."""
    
    query = db.query(Tenant)
    
    if current_user.role == "tenant_admin":
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant admin must belong to a tenant"
            )
        query = query.filter(Tenant.id == current_user.tenant_id)
    
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
    
    total = query.count()
    
    tenants = query.order_by(Tenant.created_at.desc()).offset(skip).limit(limit).all()
    
    comprehensive_tenants = []
    total_tenant_admins = 0
    total_organizations = 0
    total_users = 0
    
    for tenant in tenants:
        tenant_admins = db.query(User).filter(
            and_(User.tenant_id == tenant.id, User.role == "tenant_admin")
        ).all()
        
        tenant_admin_info = [
            TenantAdminInfo(
                id=str(admin.id),
                email=admin.email,
                username=admin.username,
                full_name=admin.full_name,
                role=admin.role,
                is_active=admin.is_active,
                created_at=admin.created_at,
                last_login=admin.last_login
            ) for admin in tenant_admins
        ]
        
        organizations = db.query(Organization).filter(Organization.tenant_id == tenant.id).all()
        
        detailed_orgs = []
        tenant_total_users = len(tenant_admins) 
        tenant_active_users = len([admin for admin in tenant_admins if admin.is_active])
        
        for org in organizations:
            org_admin = db.query(User).filter(
                and_(User.organization_id == org.id, User.role == "org_admin")
            ).first()
            
            org_admin_info = None
            if org_admin:
                org_admin_info = OrganizationAdminInfo(
                    id=str(org_admin.id),
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
            
            org_member_info = [
                OrganizationUserInfo(
                    id=str(member.id),
                    email=member.email,
                    username=member.username,
                    full_name=member.full_name,
                    role=member.role,
                    is_active=member.is_active,
                    created_at=member.created_at
                ) for member in org_members
            ]
            
            org_total_users = len(org_members) + (1 if org_admin else 0)
            tenant_total_users += org_total_users
            tenant_active_users += len([m for m in org_members if m.is_active]) + (1 if org_admin and org_admin.is_active else 0)
            
            detailed_org = DetailedOrganizationInfo(
                id=str(org.id),
                name=org.name,
                slug=org.slug,
                description=org.description,
                is_active=org.is_active,
                join_token=org.join_token,
                join_enabled=org.join_enabled,
                default_role=org.default_role,
                max_users=org.max_users,
                created_at=org.created_at,
                updated_at=org.updated_at,
                admin=org_admin_info,
                members=org_member_info,
                total_users=org_total_users
            )
            detailed_orgs.append(detailed_org)
        
        comprehensive_tenant = ComprehensiveTenantResponse(
            id=str(tenant.id),
            name=tenant.name,
            slug=tenant.slug,
            domain=tenant.domain,
            description=tenant.description,
            logo_url=tenant.logo_url,
            is_active=tenant.is_active,
            created_by=str(tenant.created_by),
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
            tenant_admins=tenant_admin_info,
            total_tenant_admins=len(tenant_admin_info),
            organizations=detailed_orgs,
            total_organizations=len(detailed_orgs),
            active_organizations=len([org for org in detailed_orgs if org.is_active]),
            total_users_in_tenant=tenant_total_users,
            total_active_users=tenant_active_users
        )
        
        comprehensive_tenants.append(comprehensive_tenant)
        total_tenant_admins += len(tenant_admin_info)
        total_organizations += len(detailed_orgs)
        total_users += tenant_total_users
    
    return ComprehensiveTenantListResponse(
        tenants=comprehensive_tenants,
        total=total,
        skip=skip,
        limit=limit,
        total_tenant_admins=total_tenant_admins,
        total_organizations=total_organizations,
        total_users=total_users
    )

@router.get("/{tenant_id}", response_model=ComprehensiveTenantResponse)
async def get_tenant(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above)
):
    """Get comprehensive tenant details - Super Admin can access any tenant, Tenant Admin can access their own tenant."""
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if current_user.role == "tenant_admin":
        if str(current_user.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
    
    tenant_admins = db.query(User).filter(
        and_(User.tenant_id == tenant.id, User.role == "tenant_admin")
    ).all()
    
    tenant_admin_info = [
        TenantAdminInfo(
            id=str(admin.id),
            email=admin.email,
            username=admin.username,
            full_name=admin.full_name,
            role=admin.role,
            is_active=admin.is_active,
            created_at=admin.created_at,
            last_login=admin.last_login
        ) for admin in tenant_admins
    ]
    
    organizations = db.query(Organization).filter(Organization.tenant_id == tenant.id).all()
    
    detailed_orgs = []
    tenant_total_users = len(tenant_admins)  
    tenant_active_users = len([admin for admin in tenant_admins if admin.is_active])
    
    for org in organizations:
        org_admin = db.query(User).filter(
            and_(User.organization_id == org.id, User.role == "org_admin")
        ).first()
        
        org_admin_info = None
        if org_admin:
            org_admin_info = OrganizationAdminInfo(
                id=str(org_admin.id),
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
        
        org_member_info = [
            OrganizationUserInfo(
                id=str(member.id),
                email=member.email,
                username=member.username,
                full_name=member.full_name,
                role=member.role,
                is_active=member.is_active,
                created_at=member.created_at
            ) for member in org_members
        ]
        
        org_total_users = len(org_members) + (1 if org_admin else 0)
        tenant_total_users += org_total_users
        tenant_active_users += len([m for m in org_members if m.is_active]) + (1 if org_admin and org_admin.is_active else 0)
        
        detailed_org = DetailedOrganizationInfo(
            id=str(org.id),
            name=org.name,
            slug=org.slug,
            description=org.description,
            is_active=org.is_active,
            join_token=org.join_token,
            join_enabled=org.join_enabled,
            default_role=org.default_role,
            max_users=org.max_users,
            created_at=org.created_at,
            updated_at=org.updated_at,
            admin=org_admin_info,
            members=org_member_info,
            total_users=org_total_users
        )
        detailed_orgs.append(detailed_org)
    
    return ComprehensiveTenantResponse(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        domain=tenant.domain,
        description=tenant.description,
        logo_url=tenant.logo_url,
        is_active=tenant.is_active,
        created_by=str(tenant.created_by),
        created_at=tenant.created_at,
        updated_at=tenant.updated_at,
        tenant_admins=tenant_admin_info,
        total_tenant_admins=len(tenant_admins),
        organizations=detailed_orgs,
        total_organizations=len(organizations),
        active_organizations=len([org for org in organizations if org.is_active]),
        total_users_in_tenant=tenant_total_users,
        total_active_users=tenant_active_users
    )

@router.put("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    tenant_update: TenantUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above)
):
    """Update tenant information - Super Admin can update any tenant, Tenant Admin can update their own tenant."""
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if current_user.role == "tenant_admin":
        if str(current_user.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Can only update your own tenant"
            )
    
    update_data = tenant_update.dict(exclude_unset=True)
    
    if "domain" in update_data and update_data["domain"]:
        if not validate_tenant_domain(update_data["domain"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid domain format"
            )
        
        existing_domain = db.query(Tenant).filter(
            and_(Tenant.domain == update_data["domain"], Tenant.id != tenant_id)
        ).first()
        if existing_domain:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Domain already registered"
            )
    
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
    
    org_count = db.query(Organization).filter(Organization.tenant_id == tenant_id).count()
    
    if org_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant has {org_count} organizations. Use force=true to delete anyway."
        )
    
    if force and org_count > 0:
        organizations = db.query(Organization).filter(Organization.tenant_id == tenant_id).all()
        for org in organizations:
            db.delete(org)
    
    db.delete(tenant)
    db.commit()
    
    return {"message": f"Tenant '{tenant.name}' deleted successfully"}

@router.get("/{tenant_id}/stats", response_model=TenantStatsResponse)
async def get_tenant_stats(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_tenant_admin_or_above)
):
    """Get tenant statistics - Super Admin can access any tenant, Tenant Admin can access their own tenant."""
    
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    if current_user.role == "tenant_admin":
        if str(current_user.tenant_id) != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant's statistics"
            )
    
    org_count = db.query(Organization).filter(Organization.tenant_id == tenant_id).count()
    
    user_count = db.query(User).join(
        Organization, User.organization_id == Organization.id
    ).filter(
        Organization.tenant_id == tenant_id
    ).count()
    
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