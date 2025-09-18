"""
Professional Authentication System
High-performance user authentication with organization support
"""

import os
import uuid
from typing import Optional, Union
from datetime import datetime

from fastapi import Depends, Request, HTTPException, status
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import User, get_db
from .schemas import UserCreate, UserUpdate
from .email_service import send_verification_email, send_password_reset_email

# Configuration
SECRET = os.getenv("SECRET_KEY", "your-secret-key-here")
VERIFICATION_TOKEN_SECRET = os.getenv("VERIFICATION_TOKEN_SECRET", "verification-secret")
RESET_PASSWORD_TOKEN_SECRET = os.getenv("RESET_PASSWORD_TOKEN_SECRET", "reset-secret")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Enhanced user manager with organization support"""
    
    reset_password_token_secret = RESET_PASSWORD_TOKEN_SECRET
    verification_token_secret = VERIFICATION_TOKEN_SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Called after a user registers - send verification email"""
        print(f"✅ User {user.email} registered successfully")
        
        if not user.is_verified:
            # Generate verification token and send email
            token = await self.request_verify(user, request)
            await send_verification_email(user.email, user.full_name or user.username, token)
            print(f"📧 Verification email sent to {user.email}")

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response = None,
    ):
        """Called after successful login - update last_login"""
        print(f"🔑 User {user.email} logged in successfully")
        
        # Update last login time in database
        db = next(get_db())
        try:
            db_user = db.query(User).filter(User.id == user.id).first()
            if db_user:
                db_user.last_login = datetime.utcnow()
                db.commit()
        except Exception as e:
            print(f"⚠️ Could not update last login: {str(e)}")
        finally:
            db.close()

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after password reset request"""
        print(f"🔑 Password reset requested for {user.email}")
        await send_password_reset_email(user.email, user.full_name or user.username, token)
        print(f"📧 Password reset email sent to {user.email}")

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after verification request"""
        print(f"📧 Email verification requested for {user.email}")
        await send_verification_email(user.email, user.full_name or user.username, token)

    async def on_after_verify(
        self, user: User, request: Optional[Request] = None
    ):
        """Called after successful email verification"""
        print(f"✅ Email verified for {user.email}")

    async def create(
        self,
        user_create: UserCreate,
        safe: bool = False,
        request: Optional[Request] = None,
    ) -> User:
        """Create a new user with organization support"""
        await self.validate_password(user_create.password, user_create)

        existing_user = await self.user_db.get_by_email(user_create.email)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        user_dict = user_create.dict()
        password = user_dict.pop("password")
        user_dict.pop("confirm_password", None)  # Remove confirm_password
        user_dict["hashed_password"] = self.password_helper.hash(password)
        
        # Set default values for organization fields
        user_dict["organization_role"] = "user"
        user_dict["global_role"] = "user"
        user_dict["is_active"] = True
        user_dict["is_verified"] = False  # Require email verification
        user_dict["organization_id"] = None  # No organization initially
        
        created_user = await self.user_db.create(user_dict)
        await self.on_after_register(created_user, request)
        return created_user

# User database adapter
async def get_user_db(session: Session = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)

# User manager dependency
async def get_user_manager(user_db: SQLAlchemyUserDatabase = Depends(get_user_db)):
    yield UserManager(user_db)

# Authentication backend setup
bearer_transport = BearerTransport(tokenUrl="auth/login")

jwt_strategy = JWTStrategy(
    secret=SECRET,
    lifetime_seconds=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=lambda: jwt_strategy,
)

# Main authentication instance
auth_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Dependencies for route protection
current_active_user = auth_users.current_user(active=True)
current_verified_user = auth_users.current_user(active=True, verified=True)

# Organization-specific dependencies
def require_organization_member(user: User = Depends(current_verified_user)):
    """Require user to belong to an organization"""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must belong to an organization to access this resource"
        )
    return user

def require_organization_admin(user: User = Depends(current_verified_user)):
    """Require user to be an organization admin"""
    if not user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must belong to an organization"
        )
    if user.organization_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization admin privileges required"
        )
    return user

def require_global_admin(user: User = Depends(current_verified_user)):
    """Require user to be a global admin or super admin"""
    if user.global_role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Global admin privileges required"
        )
    return user

def require_super_admin(user: User = Depends(current_verified_user)):
    """Require user to be a super admin"""
    if user.global_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required"
        )
    return user

# Additional convenience dependencies
def get_user_organization_context(user: User = Depends(current_verified_user)):
    """Get user with organization context for data filtering"""
    return {
        "user": user,
        "organization_id": user.organization_id,
        "global_role": user.global_role,
        "organization_role": user.organization_role,
        "can_see_global": True,  # All users can see global data
        "can_see_organization": user.organization_id is not None,
        "can_see_personal": True,  # All users can see their personal data
    }

def get_data_access_filter(user: User = Depends(current_verified_user)):
    """Get data access filter for queries"""
    return {
        "user_id": user.id,
        "organization_id": user.organization_id,
        "is_super_admin": user.global_role == "super_admin",
        "is_global_admin": user.global_role in ["admin", "super_admin"],
        "is_org_admin": user.organization_role == "admin",
    }
