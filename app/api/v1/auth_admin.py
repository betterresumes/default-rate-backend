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

def require_super_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require super admin role."""
    if current_user.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return current_user

def require_tenant_admin_or_above(current_user: User = Depends(get_current_active_user)) -> User:
    """Require tenant admin role or above."""
    if current_user.role not in ["super_admin", "tenant_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant admin privileges or above required"
        )
    return current_user

def require_org_admin_or_above(current_user: User = Depends(get_current_active_user)) -> User:
    """Require organization admin role or above."""
    if current_user.role not in ["super_admin", "tenant_admin", "org_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin privileges or above required"
        )
    return current_user

def require_org_member_or_above(current_user: User = Depends(get_current_active_user)) -> User:
    """Require organization membership or above."""
    if current_user.role not in ["super_admin", "tenant_admin", "org_admin", "org_member"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization membership or above required"
        )
    return current_user

def require_any_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require any admin role (super_admin, tenant_admin, or org_admin)."""
    if current_user.role not in ["super_admin", "tenant_admin", "org_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


@router.post("/create-user", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def admin_create_user(
    user_data: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_admin)
):
    """Create a new user account (Admin only) - with organization assignment."""
    
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    full_name = user_data.full_name
    if user_data.first_name or user_data.last_name:
        full_name = f"{user_data.first_name or ''} {user_data.last_name or ''}".strip()
    
    username = user_data.username or user_data.email.split("@")[0]
    
    import re
    username = re.sub(r'[^a-zA-Z0-9_-]', '_', username)
    if not username or len(username) < 2:
        username = "user"
    
    existing_username = db.query(User).filter(User.username == username).first()
    if existing_username:
        if user_data.username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Username '{user_data.username}' is already taken"
            )
        else:
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
    
    user_role = getattr(user_data, 'role', 'user') or 'user'
    
    if current_user.role == "super_admin":
        pass
    elif current_user.role == "tenant_admin":
        if user_role not in ["user", "org_admin", "org_member"]:
            raise HTTPException(
                status_code=403,
                detail="Tenant admins can only create users with 'user', 'org_admin', or 'org_member' roles"
            )
    else:
        if user_role != "user":
            user_role = "user"
    
    hashed_password = AuthManager.get_password_hash(user_data.password)
    
    try:
        new_user = User(
            id=uuid.uuid4(),
            email=user_data.email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            role=user_role,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return UserResponse.model_validate(new_user)
        
    except Exception as e:
        db.rollback()
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