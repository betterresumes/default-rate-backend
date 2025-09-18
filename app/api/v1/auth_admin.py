from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from typing import Optional, Union
import uuid

from ...core.database import get_db, User, Organization, Tenant, OrganizationMemberWhitelist
from ...schemas.schemas import (
    UserCreate, UserLogin, UserResponse, Token, 
    JoinOrganizationRequest, JoinOrganizationResponse
)
from ...utils.tenant_utils import is_email_whitelisted, get_organization_by_token
from .auth_multi_tenant import AuthManager, get_current_active_user

router = APIRouter(prefix="/admin", tags=["Admin Authentication"])

# Admin permission validators
def require_super_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require super admin role."""
    if current_user.global_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user

def require_tenant_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require tenant admin role."""
    if current_user.global_role not in ["super_admin", "tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin privileges required"
        )
    return current_user

def require_org_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require organization admin role."""
    if (current_user.global_role not in ["super_admin", "tenant_admin"] and 
        current_user.organization_role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin privileges required"
        )
    return current_user

def require_any_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require any admin role (super_admin, tenant_admin, or org_admin)."""
    if (current_user.global_role not in ["super_admin", "tenant_admin"] and 
        current_user.organization_role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

# =============================================
# ADMIN-ONLY AUTHENTICATION ENDPOINTS
# =============================================

@router.post("/create-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user_data: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_admin)
):
    """Create a new user account (Admin only) - with organization assignment."""
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Handle full_name - accept both full_name and first_name/last_name formats
    full_name = user_data.full_name
    if user_data.first_name or user_data.last_name:
        full_name = f"{user_data.first_name or ''} {user_data.last_name or ''}".strip()
    
    # Determine username - use provided username or generate from email
    username = user_data.username or user_data.email.split("@")[0]
    
    # Sanitize username - remove invalid characters
    import re
    username = re.sub(r'[^a-zA-Z0-9_-]', '_', username)
    if not username or len(username) < 2:
        username = "user"
    
    # Check username availability and auto-generate if needed
    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        if user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user_data.username}' is already taken"
            )
        else:
            # Auto-generate unique username
            base_username = username
            counter = 1
            max_attempts = 100
            
            while existing_username and counter <= max_attempts:
                username = f"{base_username}_{counter}"
                existing_username = db.query(User).filter(User.username == username).first()
                counter += 1
            
            if existing_username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unable to generate unique username. Please provide custom username."
                )
    
    # Admin role validation
    global_role = getattr(user_data, 'global_role', 'user') or 'user'
    
    # Validate admin can assign this role
    if current_user.global_role == "super_admin":
        # Super admin can assign any role
        pass
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can assign tenant_admin, user roles
        if global_role not in ["user", "tenant_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tenant admin can only assign 'user' or 'tenant_admin' roles"
            )
    else:
        # Org admin can only assign user role
        if global_role != "user":
            global_role = "user"
    
    # Create new user account
    hashed_password = AuthManager.get_password_hash(user_data.password)
    
    try:
        new_user = User(
            id=uuid.uuid4(),
            email=user_data.email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            global_role=global_role,
            organization_role=None,  # Set later if organization assigned
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse.from_orm(new_user)
        
    except Exception as e:
        db.rollback()
        # Handle database errors
        error_str = str(e).lower()
        if "duplicate key" in error_str and "username" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{username}' is already taken"
            )
        elif "duplicate key" in error_str and "email" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' is already registered"
            )
        else:
            import logging
            logging.error(f"Admin user creation error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error during user creation"
            )

@router.post("/impersonate/{user_id}", response_model=Token)
async def admin_impersonate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Impersonate another user (Super Admin only)."""
    
    # Find target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if not target_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot impersonate inactive user"
        )
    
    # Create access token for target user
    access_token_expires = timedelta(minutes=30)  # Shorter expiry for impersonation
    access_token = AuthManager.create_access_token(
        data={
            "sub": str(target_user.id),
            "impersonated_by": str(current_user.id),
            "impersonation": True
        }, 
        expires_delta=access_token_expires
    )
    
    # Log impersonation
    import logging
    logging.warning(f"IMPERSONATION: Admin {current_user.email} ({current_user.id}) impersonating user {target_user.email} ({target_user.id})")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 30 * 60,  # 30 minutes
        "impersonating": target_user.email,
        "impersonated_by": current_user.email
    }

@router.post("/force-password-reset/{user_id}")
async def admin_force_password_reset(
    user_id: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_admin)
):
    """Force password reset for a user (Admin only)."""
    
    # Find target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check admin permissions
    can_reset = False
    if current_user.global_role == "super_admin":
        can_reset = True
    elif current_user.global_role == "tenant_admin":
        # Tenant admin can reset passwords for users in their tenant
        if target_user.organization_id:
            org = db.query(Organization).filter(Organization.id == target_user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_reset = True
    elif current_user.organization_role == "admin":
        # Org admin can reset passwords for users in their organization
        if str(target_user.organization_id) == str(current_user.organization_id):
            can_reset = True
    
    if not can_reset:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to reset this user's password"
        )
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Update password
    target_user.hashed_password = AuthManager.get_password_hash(new_password)
    target_user.updated_at = datetime.utcnow()
    
    db.commit()
    
    # Log password reset
    import logging
    logging.warning(f"PASSWORD RESET: Admin {current_user.email} reset password for user {target_user.email}")
    
    return {
        "message": f"Password reset successfully for user {target_user.email}",
        "user_id": str(target_user.id),
        "reset_by": current_user.email
    }

@router.get("/audit/login-history/{user_id}")
async def admin_get_user_login_history(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_admin)
):
    """Get login history for a user (Admin only)."""
    
    # Find target user
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check admin permissions
    can_view = False
    if current_user.global_role == "super_admin":
        can_view = True
    elif current_user.global_role == "tenant_admin":
        if target_user.organization_id:
            org = db.query(Organization).filter(Organization.id == target_user.organization_id).first()
            if org and org.tenant_id == current_user.tenant_id:
                can_view = True
    elif current_user.organization_role == "admin":
        if str(target_user.organization_id) == str(current_user.organization_id):
            can_view = True
    
    if not can_view:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient privileges to view this user's login history"
        )
    
    return {
        "user_id": str(target_user.id),
        "email": target_user.email,
        "last_login": target_user.last_login,
        "created_at": target_user.created_at,
        "is_active": target_user.is_active,
        "organization_id": str(target_user.organization_id) if target_user.organization_id else None
    }

@router.post("/bulk-activate")
async def admin_bulk_activate_users(
    user_ids: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_admin)
):
    """Bulk activate multiple users (Admin only)."""
    
    if len(user_ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process more than 100 users at once"
        )
    
    activated_users = []
    failed_users = []
    
    for user_id in user_ids:
        try:
            target_user = db.query(User).filter(User.id == user_id).first()
            if not target_user:
                failed_users.append({"user_id": user_id, "reason": "User not found"})
                continue
            
            # Check permissions
            can_activate = False
            if current_user.global_role == "super_admin":
                can_activate = True
            elif current_user.global_role == "tenant_admin":
                if target_user.organization_id:
                    org = db.query(Organization).filter(Organization.id == target_user.organization_id).first()
                    if org and org.tenant_id == current_user.tenant_id:
                        can_activate = True
            elif current_user.organization_role == "admin":
                if str(target_user.organization_id) == str(current_user.organization_id):
                    can_activate = True
            
            if not can_activate:
                failed_users.append({"user_id": user_id, "reason": "Insufficient privileges"})
                continue
            
            target_user.is_active = True
            target_user.updated_at = datetime.utcnow()
            activated_users.append({
                "user_id": str(target_user.id),
                "email": target_user.email
            })
            
        except Exception as e:
            failed_users.append({"user_id": user_id, "reason": str(e)})
    
    db.commit()
    
    return {
        "message": f"Bulk activation completed. {len(activated_users)} users activated, {len(failed_users)} failed",
        "activated_users": activated_users,
        "failed_users": failed_users,
        "processed_by": current_user.email
    }
