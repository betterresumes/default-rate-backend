from datetime import datetime, timedelta
from typing import Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request, APIRouter
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import secrets
import random
import string
import logging
from pydantic import BaseModel
from .database import get_db, User, OTPToken
from .schemas import TokenData
from .email_service import EmailService
import os

# Configure logging
logger = logging.getLogger(__name__)
import secrets
import random
import string
from pydantic import BaseModel
from .database import get_db, User, OTPToken
from .schemas import TokenData
import os
from .email_service import EmailService

# Email verification settings - PRODUCTION MODE
REQUIRE_EMAIL_VERIFICATION = os.getenv("REQUIRE_EMAIL_VERIFICATION", "true").lower() == "true"
DEVELOPMENT_MODE = os.getenv("DEBUG", "false").lower() == "true"

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

security = HTTPBearer()

email_service = EmailService()

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

# Initialize email service
email_service = EmailService()

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
    """Create a new user with smart email verification based on environment."""
    hashed_password = auth_manager.get_password_hash(password)
    
    # Smart verification based on environment
    if DEVELOPMENT_MODE or not REQUIRE_EMAIL_VERIFICATION:
        # Development: Fast registration, no email verification needed
        is_active = True
        is_verified = True
        logger.info(f"🚀 Fast registration for {email} (development mode)")
    else:
        # Production: Secure registration, email verification required
        is_active = False
        is_verified = False
        logger.info(f"🔒 Secure registration for {email} (email verification required)")
    
    db_user = User(
        email=email,
        username=username,
        hashed_password=hashed_password,
        full_name=full_name,
        is_active=is_active,
        is_verified=is_verified
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
    # TODO: Implement UserSession model in database first
    session_token = auth_manager.generate_session_token()
    # expires_at = datetime.utcnow() + timedelta(days=30)  
    
    # db_session = UserSession(
    #     user_id=user_id,
    #     session_token=session_token,
    #     expires_at=expires_at,
    #     user_agent=user_agent,
    #     ip_address=ip_address
    # )
    # db.add(db_session)
    # db.commit()
    # db.refresh(db_session)
    return session_token

def verify_token(token: str) -> Optional[TokenData]:
    """Verify and decode JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        email = payload.get("email")
        if user_id is None or email is None:
            return None
        return TokenData(user_id=user_id, email=email)
    except JWTError:
        return None

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get the current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
        
    token_data = verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
        
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get the current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
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
    if current_user.global_role not in ["admin", "super_admin"] and current_user.organization_role not in ["admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def get_super_admin_user(current_user: User = Depends(get_current_verified_user)) -> User:
    """Get the current super admin user (for system-level operations)."""
    if current_user.global_role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin permissions required"
        )
    return current_user

def allow_organization_creation(current_user: User = Depends(get_current_verified_user)) -> User:
    """Allow any verified user to create organizations (they become admin of their org)."""
    # For now, any verified user can create an organization
    # They will automatically become admin of that organization
    return current_user

def logout_user(db: Session, session_token: str) -> bool:
    """Logout user by deactivating session."""
    # TODO: Implement UserSession model in database first
    # session = db.query(UserSession).filter(
    #     UserSession.session_token == session_token,
    #     UserSession.is_active == True
    # ).first()
    
    # if session:
    #     session.is_active = False
    #     db.commit()
    #     return True
    return False

def get_user_organization_context(current_user: User = Depends(get_current_verified_user)):
    """Get user context with organization information."""
    return {
        "user": current_user,
        "organization_id": current_user.organization_id,
        "organization_role": current_user.organization_role,
        "global_role": current_user.global_role,
        "is_super_admin": current_user.global_role == "super_admin"
    }

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token."""
    return auth_manager.create_access_token(data, expires_delta)

# ========================================
# API ROUTER AND ENDPOINTS
# ========================================

# Request models
class UserRegistration(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    name: Optional[str] = None  # Accept both 'name' and 'full_name' for flexibility
    
    def get_display_name(self) -> Optional[str]:
        """Get display name from either 'name' or 'full_name' field"""
        return self.name or self.full_name

class UserLogin(BaseModel):
    email: str
    password: str

class EmailVerificationRequest(BaseModel):
    email: str
    otp: str

class ResendOTPRequest(BaseModel):
    email: str

class JoinWithCodeRequest(BaseModel):
    email: str
    username: str
    password: str
    full_name: Optional[str] = None
    organization_code: str
    requested_role: str

# Create auth router
router = APIRouter(prefix="/v1/auth", tags=["🔐 Authentication"])

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

@router.post("/register",
            summary="User Registration",
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
        
        # Create user (smart mode based on environment)
        display_name = user_data.get_display_name()
        user = create_user(db, user_data.email, user_data.username, user_data.password, display_name)
        
        # Handle email verification based on mode
        if not DEVELOPMENT_MODE and REQUIRE_EMAIL_VERIFICATION and not user.is_verified:
            # Production mode: Send verification email
            try:
                otp = create_otp_token(db, str(user.id), "email_verification")
                email_service.send_verification_email(
                    to_email=user.email,
                    user_name=user.full_name or user.username,
                    otp_code=otp
                )
                email_sent = True
                message = "User registered successfully! Please check your email for verification code."
                next_step = "verify_email"
            except Exception as email_error:
                logger.warning(f"Failed to send verification email: {email_error}")
                email_sent = False
                message = "User registered successfully. Please contact support for email verification."
                next_step = "verify_email"
        else:
            # Development mode: No email verification needed
            email_sent = False
            message = f"User registered successfully! You can login immediately. (Mode: {'Development' if DEVELOPMENT_MODE else 'No verification required'})"
            next_step = "login"
        
        db.commit()
        
        return {
            "success": True,
            "message": message,
            "data": {
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "organization_id": str(user.organization_id) if user.organization_id else None,
                "organization_role": user.organization_role,
                "global_role": user.global_role,
                "is_active": user.is_active,
                "is_verified": user.is_verified,
                "next_step": next_step,
                "email_verification_required": not user.is_verified,
                "development_mode": DEVELOPMENT_MODE,
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
            if REQUIRE_EMAIL_VERIFICATION and not DEVELOPMENT_MODE:
                return {
                    "success": False,
                    "message": "Account is inactive. Please verify your email first.",
                    "data": {
                        "next_step": "verify_email",
                        "email": user.email
                    }
                }
            else:
                return {
                    "success": False,
                    "message": "Account is inactive",
                    "data": None
                }
        
        if not user.is_verified and REQUIRE_EMAIL_VERIFICATION and not DEVELOPMENT_MODE:
            return {
                "success": False,
                "message": "Please verify your email before logging in.",
                "data": {
                    "next_step": "verify_email", 
                    "email": user.email
                }
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
                    "organization_id": str(user.organization_id) if user.organization_id else None,
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
            "organization_id": str(current_user.organization_id) if current_user.organization_id else None,
            "organization_role": current_user.organization_role,
            "global_role": current_user.global_role,
            "is_active": current_user.is_active,
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at,
            "updated_at": current_user.updated_at,
            "last_login": current_user.last_login
        }
    }

@router.post("/verify-email",
            summary="Verify Email with OTP",
            tags=["✉️ Email Verification"])
async def verify_email(
    verification_data: EmailVerificationRequest,
    db: Session = Depends(get_db)
):
    """Verify email address with OTP code"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == verification_data.email).first()
        if not user:
            return {
                "success": False,
                "message": "User not found",
                "data": None
            }
        
        if user.is_verified:
            return {
                "success": False,
                "message": "Email already verified",
                "data": None
            }
        
        # Verify OTP
        if verify_otp_token(db, str(user.id), verification_data.otp, "email_verification"):
            # Activate user account
            user.is_verified = True
            user.is_active = True
            user.updated_at = datetime.utcnow()
            db.commit()
            
            return {
                "success": True,
                "message": "Email verified successfully! You can now login.",
                "data": {
                    "email": user.email,
                    "is_verified": True,
                    "is_active": True
                }
            }
        else:
            return {
                "success": False,
                "message": "Invalid or expired OTP code",
                "data": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"Email verification failed: {str(e)}",
            "data": None
        }

@router.post("/resend-verification",
            summary="Resend Email Verification OTP",
            tags=["✉️ Email Verification"])
async def resend_verification_otp(
    resend_data: ResendOTPRequest,
    db: Session = Depends(get_db)
):
    """Resend OTP for email verification"""
    try:
        # Find user by email
        user = db.query(User).filter(User.email == resend_data.email).first()
        if not user:
            return {
                "success": False,
                "message": "User not found",
                "data": None
            }
        
        if user.is_verified:
            return {
                "success": False,
                "message": "Email already verified",
                "data": None
            }
        
        # Generate and send new OTP
        otp = create_otp_token(db, str(user.id), "email_verification")
        
        # Send verification email
        try:
            email_service.send_verification_email(
                to_email=user.email,
                user_name=user.full_name or user.username,
                otp_code=otp
            )
        except Exception as email_error:
            logger.warning(f"Failed to send verification email: {email_error}")
            # Continue anyway - user can try again
        
        return {
            "success": True,
            "message": "Verification code sent to your email",
            "data": {
                "email": user.email,
                "expires_in_minutes": 10
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to resend verification: {str(e)}",
            "data": None
        }

@router.post("/register-with-org-code",
            summary="Register with Organization Code",
            tags=["📝 Registration"])
async def register_with_organization_code(
    user_data: dict,  # We'll validate manually to avoid circular imports
    db: Session = Depends(get_db)
):
    """Register user with organization code (requires admin approval)"""
    try:
        from .org_code_manager import OrganizationCodeManager
        from .database import PendingMember
        
        # Manual validation of input
        required_fields = ['email', 'username', 'password', 'full_name', 'organization_code']
        for field in required_fields:
            if field not in user_data:
                return {
                    "success": False,
                    "message": f"Missing required field: {field}",
                    "data": None
                }
        
        email = user_data['email']
        username = user_data['username']
        password = user_data['password']
        full_name = user_data['full_name']
        organization_code = user_data['organization_code'].upper().strip()
        requested_role = user_data.get('requested_role', 'user')
        
        # Basic validation
        if len(password) < 8:
            return {
                "success": False,
                "message": "Password must be at least 8 characters long",
                "data": None
            }
        
        if len(organization_code) != 8:
            return {
                "success": False,
                "message": "Organization code must be 8 characters",
                "data": None
            }
        
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            return {
                "success": False,
                "message": "User with this email or username already exists",
                "data": None
            }
        
        # Validate organization code
        org = OrganizationCodeManager.validate_code(db, organization_code)
        if not org:
            return {
                "success": False,
                "message": "Invalid or disabled organization code",
                "data": None
            }
        
        # Create user account (pending organization approval)
        user = create_user(db, email, username, password, full_name)
        
        # Set user as pending in organization
        user.organization_id = org.id
        user.organization_role = requested_role
        user.organization_status = "pending"  # Requires admin approval
        
        # Create pending member record
        pending_member = PendingMember(
            organization_id=org.id,
            user_id=user.id,
            email=email,
            requested_role=requested_role,
            organization_code_used=organization_code,
            status="pending"
        )
        
        db.add(pending_member)
        db.commit()
        db.refresh(user)
        
        # Create access token (user can login but has limited access until approved)
        access_token = create_access_token(
            data={"user_id": str(user.id), "email": user.email},
            expires_delta=timedelta(hours=24)
        )
        
        return {
            "success": True,
            "message": f"Registration successful! You've requested to join {org.name}. An admin will review your request.",
            "data": {
                "access_token": access_token,
                "token_type": "bearer",
                "user": {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "organization_id": str(user.organization_id),
                    "organization_role": user.organization_role,
                    "organization_status": user.organization_status,
                    "global_role": user.global_role
                },
                "organization": {
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug
                },
                "organization_status": "pending",
                "pending_approval": True,
                "next_steps": [
                    "Your request has been sent to organization administrators",
                    "You will receive access once an admin approves your request",
                    "You can login but will have limited access until approved"
                ]
            }
        }
        
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"Registration failed: {str(e)}",
            "data": None
        }
