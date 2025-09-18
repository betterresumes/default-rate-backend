from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import secrets
import random
import string
from .database import get_db, User, OTPToken
from .schemas import TokenData
import os

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer()

class AuthManager:
    def __init__(self):
        self.pwd_context = pwd_context
        
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        """Create a JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id: int = payload.get("sub")
            if user_id is None:
                return None
            token_data = TokenData(user_id=user_id)
            return token_data
        except JWTError:
            return None
    
    def generate_otp(self) -> str:
        """Generate a 6-digit OTP."""
        return ''.join(random.choices(string.digits, k=6))
    
    def generate_session_token(self) -> str:
        """Generate a secure session token."""
        return secrets.token_urlsafe(32)

auth_manager = AuthManager()

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user with email and password."""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not auth_manager.verify_password(password, user.hashed_password):
        return None
    return user

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email."""
    return db.query(User).filter(User.email == email).first()

def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username."""
    return db.query(User).filter(User.username == username).first()

def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    """Get user by ID."""
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, email: str, username: str, password: str, full_name: Optional[str] = None) -> User:
    """Create a new user."""
    hashed_password = auth_manager.get_password_hash(password)
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=True,   # Set as active for direct login - TODO: Change back to False when implementing OTP
        is_verified=False  # Keep as False for now, can be verified later via OTP
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def create_otp_token(db: Session, user_id: int, token_type: str) -> str:
    """Create an OTP token for a user."""
    db.query(OTPToken).filter(
        OTPToken.user_id == user_id,
        OTPToken.token_type == token_type,
        OTPToken.is_used == False
    ).update({"is_used": True})
    
    otp = auth_manager.generate_otp()
    expires_at = datetime.utcnow() + timedelta(minutes=10)  
    
    db_otp = OTPToken(
        user_id=user_id,
        token=otp,
        token_type=token_type,
        expires_at=expires_at
    )
    db.add(db_otp)
    db.commit()
    db.refresh(db_otp)
    return otp

def verify_otp_token(db: Session, user_id: int, token: str, token_type: str) -> bool:
    """Verify an OTP token."""
    otp_record = db.query(OTPToken).filter(
        OTPToken.user_id == user_id,
        OTPToken.token == token,
        OTPToken.token_type == token_type,
        OTPToken.is_used == False,
        OTPToken.expires_at > datetime.utcnow()
    ).first()
    
    if otp_record:
        otp_record.is_used = True
        db.commit()
        return True
    return False

def create_user_session(db: Session, user_id: int, user_agent: Optional[str] = None, ip_address: Optional[str] = None) -> str:
    """Create a user session."""
    session_token = auth_manager.generate_session_token()
    expires_at = datetime.utcnow() + timedelta(days=30)  
    
    db_session = UserSession(
        user_id=user_id,
        session_token=session_token,
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return session_token

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_data = auth_manager.verify_token(credentials.credentials)
        if token_data is None:
            raise credentials_exception
        
        user = get_user_by_id(db, user_id=token_data.user_id)
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        return user
    except JWTError:
        raise credentials_exception

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Inactive user"
        )
    return current_user

def get_current_verified_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Get the current verified user."""
    # TODO: Re-enable email verification check later
    # if not current_user.is_verified:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Email not verified"
    #     )
    return current_user

# Alternative function for when we want to enforce verification later
def get_current_verified_user_strict(current_user: User = Depends(get_current_active_user)) -> User:
    """Get the current verified user (strict - requires email verification)."""
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified"
        )
    return current_user

def get_admin_user(current_user: User = Depends(get_current_verified_user)) -> User:
    """Get the current admin user."""
    if current_user.role not in ["admin", "superuser"] and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def logout_user(db: Session, session_token: str) -> bool:
    """Logout user by deactivating session."""
    session = db.query(UserSession).filter(
        UserSession.session_token == session_token,
        UserSession.is_active == True
    ).first()
    
    if session:
        session.is_active = False
        db.commit()
        return True
    return False
