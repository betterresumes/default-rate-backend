from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid
from datetime import datetime

from ..database import get_db, User, Organization, Tenant
from ..schemas import (
    UserResponse, UserUpdate, UserListResponse,
    UserRoleUpdate, UserRoleUpdateResponse
)
from .auth_multi_tenant import (
    require_super_admin, require_tenant_admin, require_org_admin,
    get_current_active_user
)

router = APIRouter(prefix="/users", tags=["User Management"])

@router.get("/profile", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user)
):
    """Get current user profile information."""
    return UserResponse.from_orm(current_user)

@router.put("/profile", response_model=UserResponse)
async def update_current_user_profile(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update current user profile."""
    
    # Check if username is being changed and is available
    if user_update.username and user_update.username != current_user.username:
        existing_username = db.query(User).filter(
            and_(User.username == user_update.username, User.id != current_user.id)
        ).first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
    
    # Update user fields
    update_data = user_update.dict(exclude_unset=True, exclude={"email"})  # Email cannot be changed
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)

@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
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
    
    # Apply role-based filtering
    if current_user.global_role == "super_admin":
        # Super admin can see all users
        if organization_id:
            query = query.filter(User.organization_id == organization_id)
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can see users from their tenant's organizations
        if not current_user.tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant admin must belong to a tenant"
            )
        
        # Get all organizations under this tenant
        tenant_orgs = db.query(Organization).filter(
            Organization.tenant_id == current_user.tenant_id
        ).all()
        tenant_org_ids = [str(org.id) for org in tenant_orgs]
        
        if tenant_org_ids:
            query = query.filter(User.organization_id.in_(tenant_org_ids))
        else:
            # No organizations in tenant
            return UserListResponse(users=[], total=0, skip=skip, limit=limit)
        
        # Apply organization filter if specified
        if organization_id:
            if organization_id not in tenant_org_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Organization not in your tenant"
                )
            query = query.filter(User.organization_id == organization_id)
    
    elif current_user.organization_role == "admin":
        # Organization admin can see users from their organization
        if not current_user.organization_id:
            return UserListResponse(users=[], total=0, skip=skip, limit=limit)
        
        query = query.filter(User.organization_id == current_user.organization_id)
    else:
        # Regular users can only see themselves
        query = query.filter(User.id == current_user.id)
    
    # Apply search filter
    if search:
        query = query.filter(
            or_(
                User.full_name.ilike(f"%{search}%"),
                User.email.ilike(f"%{search}%"),
                User.username.ilike(f"%{search}%")
            )
        )
    
    # Apply role filter
    if role:
        if role in ["super_admin", "tenant_admin"]:
            query = query.filter(User.global_role == role)
        else:
            query = query.filter(User.organization_role == role)
    
    # Apply active filter
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    
    return UserListResponse(
        users=[UserResponse.from_orm(user) for user in users],
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
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
    
    # Check access permissions
    if current_user.global_role == "super_admin":
        # Super admin can access any user
        pass
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can access users from their tenant's organizations
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if not org or org.tenant_id != current_user.tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to this user"
                )
    elif current_user.organization_role == "admin":
        # Organization admin can access users from their organization
        if str(user.organization_id) != str(current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this user"
            )
    else:
        # Regular users can only access themselves
        if str(user.id) != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this user"
            )
    
    return UserResponse.from_orm(user)

@router.put("/{user_id}/role", response_model=UserRoleUpdateResponse)
async def update_user_role(
    user_id: str,
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
    
    # Determine what roles current user can assign
    can_assign_global = False
    can_assign_org = False
    
    if current_user.global_role == "super_admin":
        can_assign_global = True
        can_assign_org = True
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can assign tenant admin and org roles within their tenant
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_assign_global = True  # Can assign tenant_admin
                can_assign_org = True
        else:
            can_assign_global = True  # Can assign tenant_admin to users without org
    elif current_user.organization_role == "admin":
        # Organization admin can only assign org roles within their organization
        if str(user.organization_id) == str(current_user.organization_id):
            can_assign_org = True
    
    if not (can_assign_global or can_assign_org):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to update user roles"
        )
    
    # Validate role assignments
    if role_update.global_role is not None:
        if not can_assign_global:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign global roles"
            )
        
        # Validate global role value
        if role_update.global_role not in ["user", "tenant_admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid global role"
            )
        
        # Only super admin can assign super_admin role
        if role_update.global_role == "super_admin" and current_user.global_role != "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only super admin can assign super admin role"
            )
    
    if role_update.organization_role is not None:
        if not can_assign_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot assign organization roles"
            )
        
        # Validate organization role value
        if role_update.organization_role not in ["user", "member", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization role"
            )
        
        # User must belong to an organization to have org role
        if not user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an organization to have organization role"
            )
    
    # Apply role updates
    old_global_role = user.global_role
    old_org_role = user.organization_role
    
    if role_update.global_role is not None:
        user.global_role = role_update.global_role
    
    if role_update.organization_role is not None:
        user.organization_role = role_update.organization_role
    
    user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(user)
    
    return UserRoleUpdateResponse(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        old_global_role=old_global_role,
        new_global_role=user.global_role,
        old_organization_role=old_org_role,
        new_organization_role=user.organization_role,
        updated_by=str(current_user.id),
        updated_at=user.updated_at
    )

@router.delete("/{user_id}")
async def remove_user(
    user_id: str,
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
    
    # Check permissions
    can_remove = False
    
    if current_user.global_role == "super_admin":
        can_remove = True
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can remove users from their tenant's organizations
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_remove = True
    elif current_user.organization_role == "admin":
        # Organization admin can remove users from their organization
        if str(user.organization_id) == str(current_user.organization_id):
            can_remove = True
    
    if not can_remove:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to remove user"
        )
    
    # Prevent self-removal
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself"
        )
    
    if remove_from_org_only:
        # Just remove from organization
        org_name = None
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            org_name = org.name if org else "Unknown"
        
        user.organization_id = None
        user.organization_role = "user"
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": f"User {user.email} removed from organization{f' {org_name}' if org_name else ''}",
            "user_account_deleted": False
        }
    else:
        # Delete user account completely
        email = user.email
        db.delete(user)
        db.commit()
        
        return {
            "message": f"User account {email} deleted completely",
            "user_account_deleted": True
        }

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
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
    
    # Check permissions (same as role update)
    can_modify = False
    
    if current_user.global_role == "super_admin":
        can_modify = True
    elif current_user.global_role == "tenant_admin":
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_modify = True
    elif current_user.organization_role == "admin":
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
async def deactivate_user(
    user_id: str,
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
    
    # Prevent self-deactivation
    if str(user.id) == str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    # Check permissions (same as role update)
    can_modify = False
    
    if current_user.global_role == "super_admin":
        can_modify = True
    elif current_user.global_role == "tenant_admin":
        if user.organization_id:
            org = db.query(Organization).filter(Organization.id == user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_modify = True
    elif current_user.organization_role == "admin":
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
