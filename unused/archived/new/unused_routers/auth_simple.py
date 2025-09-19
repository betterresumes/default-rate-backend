"""
Simple Authentication Router with working custom endpoints only
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import Optional
from datetime import timedelta, datetime
from pydantic import BaseModel

from ..database import get_db, User, Organization
from ..schemas import UserWithOrganization, UserRead
from ..auth import (
    get_current_active_user, 
    get_current_verified_user,
    get_admin_user,
    create_access_token, authenticate_user, create_user
)

# Create auth router
router = APIRouter(prefix="/v1/auth", tags=["🔐 Authentication"])

# Request models
class UserRegistration(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

# ========================================
# CUSTOM WORKING ENDPOINTS  
# ========================================

@router.get("/status",
           summary="Authentication System Status",
           tags=["⚡ System Health"])
async def auth_status():
    """Check authentication system status"""
    return {
        "success": True,
        "message": "Authentication system operational",
        "data": {
            "status": "healthy",
            "features": {
                "jwt_authentication": True,
                "email_verification": True,
                "password_reset": True,
                "organization_support": True,
                "role_based_access": True,
                "custom_endpoints": True
            }
        }
    }

@router.post("/register-simple",
            summary="Simple User Registration",
            tags=["📝 Registration"])
async def register_simple(
    user_data: UserRegistration,
    db: Session = Depends(get_db)
):
    """Register a new user with simple validation"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == user_data.email) | (User.username == user_data.username)
        ).first()
        
        if existing_user:
            return {
                "success": False,
                "message": "User with this email or username already exists",
                "data": None
            }
        
        # Create user
        user = create_user(db, user_data.email, user_data.username, user_data.password, user_data.full_name)
        db.commit()
        
        return {
            "success": True,
            "message": "User registered successfully",
            "data": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "organization_id": user.organization_id,
                "organization_role": user.organization_role,
                "global_role": user.global_role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "created_at": user.created_at,
                "updated_at": user.updated_at
            }
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"Registration failed: {str(e)}",
            "data": None
        }

@router.post("/login",
            summary="User Login",
            tags=["🔐 Login"])
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Login user and return JWT token"""
    try:
        # Authenticate user
        user = authenticate_user(db, login_data.email, login_data.password)
        if not user:
            return {
                "success": False,
                "message": "Invalid email or password",
                "data": None
            }
        
        if not user.is_active:
            return {
                "success": False,
                "message": "Account is inactive",
                "data": None
            }
        
        # Create access token
        access_token = create_access_token(
            data={"user_id": str(user.id), "email": user.email},
            expires_delta=timedelta(hours=24)
        )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": "Login successful",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": 86400,  # 24 hours in seconds
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "organization_id": user.organization_id,
                    "organization_role": user.organization_role,
                    "global_role": user.global_role,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "last_login": user.last_login
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Login failed: {str(e)}",
            "data": None
        }

@router.get("/me",
           summary="Get Current User",
           tags=["👤 User Profile"])
async def get_current_user_info(
    current_user: User = Depends(get_current_verified_user)
):
    """Get current user information"""
    return {
        "success": True,
        "message": "User information retrieved successfully",
        "data": {
            "id": str(current_user.id),
            "email": current_user.email,
            "username": current_user.username,
            "full_name": current_user.full_name,
            "organization_id": current_user.organization_id,
            "organization_role": current_user.organization_role,
            "global_role": current_user.global_role,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "last_login": current_user.last_login
        }
    }
