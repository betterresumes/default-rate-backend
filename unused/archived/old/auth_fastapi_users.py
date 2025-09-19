"""
New FastAPI-Users Authentication System
This replaces the old slow BCrypt+JOSE system with FastAPI-Users for better performance
"""

import os
import uuid
from typing import Optional, Union

from fastapi import Depends, Request, HTTPException
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTAuthentication,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.exceptions import UserAlreadyExists
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import User, get_db
from .schemas import UserCreate, UserUpdate
from .email_service import send_verification_email, send_invitation_email

# Configuration
SECRET = os.getenv("SECRET_KEY", "your-secret-key-here")
VERIFICATION_TOKEN_SECRET = os.getenv("VERIFICATION_TOKEN_SECRET", "verification-secret")
RESET_PASSWORD_TOKEN_SECRET = os.getenv("RESET_PASSWORD_TOKEN_SECRET", "reset-secret")

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Enhanced user manager with organization support"""
    
    reset_password_token_secret = RESET_PASSWORD_TOKEN_SECRET
    verification_token_secret = VERIFICATION_TOKEN_SECRET

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Called after a user registers - send verification email"""
        print(f"User {user.id} has registered.")
        
        if not user.is_verified:
            # Send verification email
            token = await self.request_verify(user, request)
            await send_verification_email(user.email, user.full_name or user.username, token)

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
    ):
        """Called after successful login - update last_login"""
        # Update last login time
        db = next(get_db())
        try:
            db_user = db.query(User).filter(User.id == user.id).first()
            if db_user:
                db_user.last_login = func.now()
                db.commit()
            print(f"User {user.id} logged in successfully")
        except Exception as e:
            print(f"Error updating last login: {str(e)}")
        finally:
            db.close()

    async def on_after_forgot_password(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after password reset request"""
        print(f"User {user.id} has forgot their password. Reset token: {token}")
        # Here you would send the reset email
        # await send_password_reset_email(user.email, token)

    async def on_after_request_verify(
        self, user: User, token: str, request: Optional[Request] = None
    ):
        """Called after verification request"""
        print(f"Verification requested for user {user.id}. Verification token: {token}")
        # Send verification email
        await send_verification_email(user.email, user.full_name or user.username, token)

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
            raise UserAlreadyExists()

        user_dict = user_create.dict()
        password = user_dict.pop("password")
        user_dict["hashed_password"] = self.password_helper.hash(password)
        
        # Set default values for organization fields
        user_dict["organization_role"] = "user"
        user_dict["global_role"] = "user"
        user_dict["is_active"] = True
        user_dict["is_verified"] = False  # Require email verification
        
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
bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")

jwt_authentication = JWTAuthentication(
    secret=SECRET,
    lifetime_seconds=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")) * 60,
    tokenUrl="auth/jwt/login",
)

auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=lambda: jwt_authentication,
)

# FastAPI-Users instance
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Dependencies for route protection
current_active_user = fastapi_users.current_user(active=True)
current_verified_user = fastapi_users.current_user(active=True, verified=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

# Organization-specific dependencies
def require_organization_member(user: User = Depends(current_verified_user)):
    """Require user to belong to an organization"""
    if not user.organization_id:
        raise HTTPException(
            status_code=403,
            detail="You must belong to an organization to access this resource"
        )
    return user

def require_organization_admin(user: User = Depends(current_verified_user)):
    """Require user to be an organization admin"""
    if not user.organization_id:
        raise HTTPException(
            status_code=403,
            detail="You must belong to an organization"
        )
    if user.organization_role not in ["admin"]:
        raise HTTPException(
            status_code=403,
            detail="Organization admin privileges required"
        )
    return user

def require_global_admin(user: User = Depends(current_verified_user)):
    """Require user to be a global admin or super admin"""
    if user.global_role not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Global admin privileges required"
        )
    return user

def require_super_admin(user: User = Depends(current_verified_user)):
    """Require user to be a super admin"""
    if user.global_role != "super_admin":
        raise HTTPException(
            status_code=403,
            detail="Super admin privileges required"
        )
    return user
