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
    JoinOrganizationRequest, JoinOrganizationResponse,
    ChangePasswordRequest, ChangePasswordResponse
)
from ...utils.tenant_utils import is_email_whitelisted, get_organization_by_token

router = APIRouter(tags=["User Authentication"])

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)
security = HTTPBearer()

class AuthManager:
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt

auth = AuthManager()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled"
        )
    
    return user

async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (creates personal account but no organization access)."""
    
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
                detail=f"Username '{user_data.username}' is already taken. Please choose a different username."
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
                    detail=f"Unable to generate a unique username from email '{user_data.email}'. Please provide a custom username."
                )
    
    hashed_password = pwd_context.hash(user_data.password)
    
    try:
        new_user = User(
            id=uuid.uuid4(),
            email=user_data.email,
            username=username,  
            full_name=full_name,
            hashed_password=hashed_password,
            role=user_data.role if hasattr(user_data, 'role') and user_data.role else "user",  
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
                detail=f"Username '{username}' is already taken. Please choose a different username."
            )
        elif "duplicate key" in error_str and "email" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Email '{user_data.email}' is already registered. Please use a different email or try logging in."
            )
        elif "violates" in error_str and "constraint" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid data provided. Please check your input and try again."
            )
        else:
            import logging
            import traceback
            
            logging.error(f"User registration error: {str(e)}")
            logging.error(f"Full traceback: {traceback.format_exc()}")
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)[:200]}..."  
            )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token."""
    
    user = db.query(User).filter(User.email == user_credentials.email).first()
    
    if not user or not AuthManager.verify_password(user_credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled"
        )
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthManager.create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/join", response_model=JoinOrganizationResponse)
async def join_organization(
    join_request: JoinOrganizationRequest, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Join an organization using a join token."""
    
    if current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a member of an organization"
        )
    
    organization = get_organization_by_token(db, join_request.join_token)
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired join token"
        )
    
    if not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization is not accepting new members"
        )
    
    if not organization.join_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization joining is currently disabled"
        )
    
    if not is_email_whitelisted(db, organization.id, current_user.email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Email {current_user.email} is not authorized to join {organization.name}"
        )
    
    current_members = db.query(User).filter(User.organization_id == organization.id).count()
    if organization.max_users and current_members >= organization.max_users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization has reached its member capacity"
        )
    
    current_user.organization_id = organization.id
    if organization.default_role == "org_member":
        new_role = "org_member"
    else:
        new_role = "org_member"
    
    current_user.role = new_role
    current_user.joined_via_token = join_request.join_token
    current_user.whitelist_email = current_user.email
    current_user.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(current_user)
    
    return JoinOrganizationResponse(
        success=True,
        message=f"Successfully joined {organization.name}",
        organization_id=str(organization.id),
        organization_name=organization.name,
        user_role=current_user.role
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(current_user: User = Depends(get_current_active_user)):
    """Refresh the access token."""
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = AuthManager.create_access_token(
        data={"sub": str(current_user.id)}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.post("/logout")
async def logout():
    """Logout user (client should discard token)."""
    return {"message": "Successfully logged out"}

@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Change user password - any authenticated user can update their password"""
    try:
        if not AuthManager.verify_password(request.current_password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect"
            )
        
        if AuthManager.verify_password(request.new_password, current_user.hashed_password):
            raise HTTPException(
                status_code=400,
                detail="New password must be different from current password"
            )
        
        new_hashed_password = AuthManager.get_password_hash(request.new_password)
        current_user.hashed_password = new_hashed_password
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(current_user)
        
        return ChangePasswordResponse(
            success=True,
            message="Password changed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error changing password: {str(e)}"
        )
