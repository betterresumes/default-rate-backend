from fastapi import APIRouter, Depends, Request, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid
from datetime import datetime

from ...core.database import get_db, User, Organization, Tenant
from ...schemas.schemas import (
    UserCreate, UserResponse, UserUpdate, UserListResponse,
    UserRoleUpdate, UserRoleUpdateResponse
)
from .auth_multi_tenant import get_current_active_user
from .auth_admin import (
    require_super_admin, require_tenant_admin_or_above, require_org_admin_or_above
)
from ...middleware.rate_limiting import (
    rate_limit_user_read, rate_limit_user_update, rate_limit_user_delete,
    rate_limit_user_create, rate_limit_api
)

router = APIRouter(tags=["User Management"])

@router.get("/profile", response_model=UserResponse)
@rate_limit_user_read
async def get_current_user_profile(
    request: Request, current_user: User = Depends(get_current_active_user)
):
    """Get current user profile information."""
    return UserResponse.from_orm(current_user)

@router.put("/profile", response_model=UserResponse)
@rate_limit_user_update
async def update_current_user_profile(
    request: Request, user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update current user profile."""
    
    if user_update.username and user_update.username != current_user.username:
        existing_username = db.query(User).filter(
            and_(User.username == user_update.username, User.id != current_user.id)
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    update_data = user_update.dict(exclude_unset=True, exclude={"email"})  
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)

@router.get("/me")
@rate_limit_user_read
async def get_current_user_profile_me(
    request: Request, db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get comprehensive current user profile information based on role and access level."""
    
    user_info = {
        "id": str(current_user.id),
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "organization_id": str(current_user.organization_id) if current_user.organization_id else None,
        "tenant_id": str(current_user.tenant_id) if current_user.tenant_id else None,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }
    
    if current_user.role == "super_admin":
        tenants = db.query(Tenant).all()
        tenant_list = []
        
        for tenant in tenants:
            tenant_orgs = db.query(Organization).filter(Organization.tenant_id == tenant.id).all()
            tenant_info = {
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "domain": tenant.domain,
                "description": tenant.description,
                "is_active": tenant.is_active,
                "organizations": [
                    {
                        "id": str(org.id),
                        "name": org.name,
                        "slug": org.slug,
                        "domain": org.domain,
                        "is_active": org.is_active,
                        "member_count": db.query(User).filter(User.organization_id == org.id).count()
                    }
                    for org in tenant_orgs
                ]
            }
            tenant_list.append(tenant_info)
        
        user_info.update({
            "access_level": "global",
            "permissions": [
                "manage_all_tenants",
                "manage_all_organizations", 
                "manage_all_users",
                "view_all_predictions",
                "create_global_predictions"
            ],
            "tenants": tenant_list,
            "total_tenants": len(tenant_list),
            "total_organizations": sum(len(t["organizations"]) for t in tenant_list)
        })
    
    elif current_user.role == "tenant_admin":
        if current_user.tenant_id:
            tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
            tenant_orgs = db.query(Organization).filter(Organization.tenant_id == current_user.tenant_id).all()
            
            if tenant:
                user_info.update({
                    "access_level": "tenant",
                    "permissions": [
                        "manage_tenant_organizations",
                        "manage_tenant_users",
                        "view_tenant_predictions"
                    ],
                    "tenant": {
                        "id": str(tenant.id),
                        "name": tenant.name,
                        "slug": tenant.slug,
                        "domain": tenant.domain,
                        "description": tenant.description,
                        "is_active": tenant.is_active,
                        "created_at": tenant.created_at.isoformat(),
                        "total_organizations": len(tenant_orgs),
                        "total_users": db.query(User).filter(User.tenant_id == tenant.id).count()
                    },
                    "organizations": [
                        {
                            "id": str(org.id),
                            "name": org.name,
                            "slug": org.slug,
                            "domain": org.domain,
                            "is_active": org.is_active,
                            "member_count": db.query(User).filter(User.organization_id == org.id).count(),
                            "admin_email": db.query(User).filter(
                                and_(User.organization_id == org.id, User.role == "org_admin")
                            ).first().email if db.query(User).filter(
                                and_(User.organization_id == org.id, User.role == "org_admin")
                            ).first() else None
                        }
                        for org in tenant_orgs
                    ]
                })
    
    elif current_user.role in ["org_admin", "org_member"]:
        if current_user.organization_id:
            organization = db.query(Organization).filter(Organization.id == current_user.organization_id).first()
            
            if organization:
                org_members = db.query(User).filter(User.organization_id == organization.id).all()
                
                tenant_info = None
                if organization.tenant_id:
                    tenant = db.query(Tenant).filter(Tenant.id == organization.tenant_id).first()
                    if tenant:
                        tenant_info = {
                            "id": str(tenant.id),
                            "name": tenant.name,
                            "domain": tenant.domain
                        }
                
                permissions = []
                if current_user.role == "org_admin":
                    permissions = [
                        "manage_organization_users",
                        "manage_organization_predictions",
                        "bulk_upload_predictions"
                    ]
                else:
                    permissions = [
                        "create_predictions",
                        "view_organization_predictions",
                        "update_own_predictions"
                    ]
                
                user_info.update({
                    "access_level": "organization",
                    "permissions": permissions,
                    "organization": {
                        "id": str(organization.id),
                        "name": organization.name,
                        "slug": organization.slug,
                        "domain": organization.domain,
                        "description": organization.description,
                        "is_active": organization.is_active,
                        "join_enabled": organization.join_enabled,
                        "default_role": organization.default_role,
                        "max_users": organization.max_users,
                        "current_users": len(org_members),
                        "created_at": organization.created_at.isoformat(),
                        "join_token": organization.join_token if current_user.role == "org_admin" else None
                    },
                    "tenant": tenant_info,
                    "organization_members": [
                        {
                            "id": str(member.id),
                            "email": member.email,
                            "full_name": member.full_name,
                            "role": member.role,
                            "is_active": member.is_active,
                            "joined_at": member.created_at.isoformat()
                        }
                        for member in org_members
                    ] if current_user.role == "org_admin" else None  
                })
    
    else: 
        user_info.update({
            "access_level": "personal",
            "permissions": [
                "create_personal_predictions",
                "view_personal_predictions",
                "view_global_predictions"
            ],
            "organization": None,
            "tenant": None
        })
    
    return user_info

@router.post("", response_model=UserResponse)
@rate_limit_user_create
async def create_user(
    request: Request, user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new user (Admin only)."""
    
    if current_user.role not in ["super_admin", "tenant_admin", "org_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users"
        )
    
    existing_user = db.query(User).filter(User.email == user_data.email.lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    if user_data.username:
        existing_username = db.query(User).filter(User.username == user_data.username).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    if current_user.role == "super_admin":
        organization_id = user_data.organization_id if hasattr(user_data, 'organization_id') else None
        tenant_id = user_data.tenant_id if hasattr(user_data, 'tenant_id') else None
    elif current_user.role == "tenant_admin":
        organization_id = user_data.organization_id if hasattr(user_data, 'organization_id') else None
        tenant_id = current_user.tenant_id
    
        if organization_id:
            org = db.query(Organization).filter(Organization.id == organization_id).first()
            if not org or org.tenant_id != tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot create user for organization outside your tenant"
                )
    else:
        organization_id = current_user.organization_id
        tenant_id = current_user.tenant_id
    
    from .auth_multi_tenant import AuthManager
    hashed_password = AuthManager.get_password_hash(user_data.password)
    
    try:
        valid_roles = ["user", "org_member", "org_admin", "tenant_admin", "super_admin"]
        requested_role = getattr(user_data, 'role', "user")
        
        if requested_role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role '{requested_role}'. Valid roles: {valid_roles}"
            )
        
        if current_user.role == "super_admin":
            user_role = requested_role
        elif current_user.role == "tenant_admin":
            allowed_roles = ["user", "org_member", "org_admin", "tenant_admin"]
            if requested_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Tenant admin can only assign roles: {allowed_roles}. Cannot assign '{requested_role}'"
                )
            user_role = requested_role
        else:
            allowed_roles = ["org_member", "org_admin"]
            if requested_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Organization admin can only assign roles: {allowed_roles}. Cannot assign '{requested_role}'"
                )
            user_role = requested_role
        
        new_user = User(
            id=uuid.uuid4(),
            email=user_data.email.lower(),
            username=user_data.username,
            hashed_password=hashed_password,
            full_name=f"{user_data.first_name or ''} {user_data.last_name or ''}".strip() or None,
            organization_id=organization_id,
            tenant_id=tenant_id,
            role=user_role,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse.from_orm(new_user)
        
    except Exception as e:
        db.rollback()
        
        error_str = str(e).lower()
        if "duplicate key" in error_str:
            if "email" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{user_data.email}' is already registered. Please use a different email."
                )
            elif "username" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Username '{user_data.username}' is already taken. Please choose a different username."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this information already exists. Please check email and username."
                )
        elif "foreign key" in error_str:
            if "organization" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid organization ID. Organization may not exist or be accessible."
                )
            elif "tenant" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid tenant ID. Tenant may not exist or be accessible."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid reference data provided. Please check organization and tenant IDs."
                )
        elif "violates" in error_str and "constraint" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid data provided. Please check all required fields and try again."
            )
        else:
            import logging
            logging.error(f"User creation error: {str(e)}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user. Please check your data and try again."
            )

@router.get("", response_model=UserListResponse)
@rate_limit_user_read
async def list_users(
    request: Request, skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    organization_id: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List users based on current user's permissions."""
    
    query = db.query(User)
    
    if current_user.role == "super_admin":
        if organization_id:
            query = query.filter(User.organization_id == organization_id)
    elif current_user.role == "tenant_admin":
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant admin must belong to a tenant"
            )
        
        tenant_orgs = db.query(Organization).filter(
            Organization.tenant_id == current_user.tenant_id
        ).all()
        tenant_org_ids = [str(org.id) for org in tenant_orgs]
        
        if tenant_org_ids:
            query = query.filter(User.organization_id.in_(tenant_org_ids))
        else:
            return UserListResponse(users=[], total=0, skip=skip, limit=limit)
        
        if organization_id:
            if organization_id not in tenant_org_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Organization not in your tenant"
                )
            query = query.filter(User.organization_id == organization_id)
    
    elif current_user.role == "org_admin":
        if not current_user.organization_id:
            return UserListResponse(users=[], total=0, skip=skip, limit=limit)
        
        query = query.filter(User.organization_id == current_user.organization_id)
    else:
        query = query.filter(User.id == current_user.id)
    
    if search:
        query = query.filter(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%")
            )
        )
    
    if role:
        query = query.filter(User.role == role)
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    total = query.count()
    
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{user_id}", response_model=UserResponse)
@rate_limit_user_read
async def get_user(
    request: Request, user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get user details."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if current_user.role == "super_admin":
        pass
    elif current_user.role == "tenant_admin":
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if not org or org.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this user"
                )
    elif current_user.role == "org_admin":
        if str(user.organization_id) != str(current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this user"
            )
    else:
        if str(user.id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this user"
            )
    
    return UserResponse.from_orm(user)

@router.put("/{user_id}", response_model=UserResponse)
@rate_limit_user_update
async def update_user(
    request: Request, user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update user information (Admin only)."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if str(user.id) != str(current_user.id):
        if current_user.role not in ["super_admin", "tenant_admin"]:
            if current_user.role != "org_admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can update other users"
                )
        
        if current_user.role == "tenant_admin":
            if user.organization_id:
                org = db.query(Organization).filter(Organization.id == user.organization_id).first()
                if not org or org.tenant_id != current_user.tenant_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Cannot update user from different tenant"
                    )
        
        elif current_user.role == "org_admin":
            if str(user.organization_id) != str(current_user.organization_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cannot update user from different organization"
                )
    
    update_data = user_update.dict(exclude_unset=True, exclude={"email"})  
    
    if "username" in update_data and update_data["username"]:
        existing_username = db.query(User).filter(
            and_(User.username == update_data["username"], User.id != user_id)
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    for field, value in update_data.items():
        setattr(user, field, value)
    
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)

@router.put("/{user_id}/role", response_model=UserRoleUpdateResponse)
@rate_limit_user_update
async def update_user_role(
    request: Request, user_id: str,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update user role (Admin only)."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if current_user.role not in ["super_admin", "tenant_admin", "org_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to update user roles"
        )
    
    if role_update.role is not None:
        valid_roles = ["user", "org_member", "org_admin", "tenant_admin", "super_admin"]
        if str(role_update.role) not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Valid roles: {', '.join(valid_roles)}"
            )
        
        requested_role = str(role_update.role)
        
        if requested_role == "super_admin" and current_user.role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can assign super admin role"
            )
        
        if requested_role == "tenant_admin":
            if current_user.role not in ["super_admin", "tenant_admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only super admin or tenant admin can assign tenant admin role"
                )
        
        if requested_role in ["org_admin", "org_member"]:
            if current_user.role not in ["super_admin", "tenant_admin", "org_admin"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient privileges to assign organization roles"
                )
            
            if not user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User must belong to an organization to have organization role"
                )
    
    old_role = user.role
    
    if role_update.role is not None:
        user.role = str(role_update.role)
    
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return UserRoleUpdateResponse(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        old_role=old_role,
        new_role=user.role,
        updated_by=str(current_user.id),
        updated_at=user.updated_at
    )

@router.delete("/{user_id}")
@rate_limit_user_delete
async def remove_user(
    request: Request, user_id: str,
    remove_from_org_only: bool = Query(False, description="Remove from organization only, don't delete account"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove user from organization or delete user account (Admin only)."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    can_remove = False
    
    if current_user.role == "super_admin":
        can_remove = True
    elif current_user.role == "tenant_admin":
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_remove = True
    elif current_user.role == "org_admin":
        if str(user.organization_id) == str(current_user.organization_id):
            can_remove = True
    
    if not can_remove:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to remove user"
        )
    
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself"
        )
    
    if remove_from_org_only:
        org_name = None
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            org_name = org.name if org else "Unknown"
        
        user.organization_id = None
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": f"User {user.email} removed from organization{f' {org_name}' if org_name else ''}",
            "user_account_deleted": False
        }
    else:
        email = user.email
        db.delete(user)
        db.commit()
        
        return {
            "message": f"User account {email} deleted completely",
            "user_account_deleted": True
        }

@router.post("/{user_id}/activate")
@rate_limit_user_update
async def activate_user(
    request: Request, user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Activate a user account (Admin only)."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    can_modify = False
    
    if current_user.role == "super_admin":
        can_modify = True
    elif current_user.role == "tenant_admin":
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_modify = True
    elif current_user.role == "org_admin":
        if str(user.organization_id) == str(current_user.organization_id):
            can_modify = True
    
    if not can_modify:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to activate user"
        )
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": f"User {user.email} activated successfully"}

@router.post("/{user_id}/deactivate")
@rate_limit_user_update
async def deactivate_user(
    request: Request, user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Deactivate a user account (Admin only)."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    can_modify = False
    
    if current_user.role == "super_admin":
        can_modify = True
    elif current_user.role == "tenant_admin":
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_modify = True
    elif current_user.role == "org_admin":
        if str(user.organization_id) == str(current_user.organization_id):
            can_modify = True
    
    if not can_modify:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to deactivate user"
        )
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": f"User {user.email} deactivated successfully"}
