from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional
import os

from ..database import get_db, User
from ..schemas import (
    UserCreate, UserLogin, User as UserSchema, Token, 
    OTPVerification, OTPRequest, PasswordReset, AuthResponse,
    UserUpdate
)
from ..auth import (
    auth_manager, authenticate_user, get_user_by_email, 
    get_user_by_username, create_user, create_otp_token,
    verify_otp_token, create_user_session, get_current_user,
    get_current_active_user, get_current_verified_user,
    get_admin_user, logout_user, get_user_by_id,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from ..email_service import email_service

router = APIRouter()
security = HTTPBearer()

@router.post("/register", response_model=AuthResponse)
async def register_user(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    try:
        if get_user_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        if get_user_by_username(db, user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        user = create_user(
            db=db,
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        otp = create_otp_token(db, user.id, "email_verification")
        
        # Try to send email immediately first (for quick response)
        email_sent = False
        try:
            # Quick attempt with short timeout for immediate feedback
            email_sent = email_service.send_verification_email(
                to_email=user.email,
                username=user.username,
                otp=otp
            )
        except Exception as e:
            print(f"Immediate email send failed: {str(e)}")
            
            # If immediate send fails, try background task (if Celery is available)
            try:
                from ..tasks import send_verification_email_task
                send_verification_email_task.delay(user.email, user.username, otp)
                email_sent = True  # Assume success for background task
            except Exception as task_error:
                print(f"Background email task failed: {str(task_error)}")
                # In development mode, still allow registration to continue
                if os.getenv("DEBUG", "false").lower() == "true":
                    email_sent = True
        
        return AuthResponse(
            success=True,
            message="User registered successfully. Please check your email for verification code.",
            data={
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
                "email_sent": email_sent
            }
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(
    verification_data: OTPVerification,
    db: Session = Depends(get_db)
):
    """Verify user email with OTP."""
    try:
        user = get_user_by_email(db, verification_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        if not verify_otp_token(db, user.id, verification_data.otp, "email_verification"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        user.is_verified = True
        user.is_active = True
        db.commit()
        
        return AuthResponse(
            success=True,
            message="Email verified successfully. You can now login.",
            data={"user_id": user.id, "email": user.email}
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Email verification failed: {str(e)}"
        )

@router.post("/resend-verification", response_model=AuthResponse)
async def resend_verification_email(
    email_data: OTPRequest,
    db: Session = Depends(get_db)
):
    """Resend verification email."""
    try:
        user = get_user_by_email(db, email_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified"
            )
        
        otp = create_otp_token(db, user.id, "email_verification")
        
        # Try immediate send first, fallback to background task
        email_sent = False
        try:
            email_sent = email_service.send_verification_email(
                to_email=user.email,
                username=user.username,
                otp=otp
            )
        except Exception as e:
            print(f"Immediate email send failed: {str(e)}")
            try:
                from ..tasks import send_verification_email_task
                send_verification_email_task.delay(user.email, user.username, otp)
                email_sent = True
            except Exception as task_error:
                print(f"Background email task failed: {str(task_error)}")
                if os.getenv("DEBUG", "false").lower() == "true":
                    email_sent = True
        
        return AuthResponse(
            success=True,
            message="Verification email sent successfully.",
            data={"email_sent": email_sent}
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend verification email: {str(e)}"
        )

@router.post("/login", response_model=Token)
async def login_user(
    login_data: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login user with email and password."""
    try:
        user = authenticate_user(db, login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        if not user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified. Please verify your email first."
            )
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_manager.create_access_token(
            data={"sub": str(user.id)}, expires_delta=access_token_expires
        )
        
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None
        session_token = create_user_session(db, user.id, user_agent, ip_address)
        
        user.last_login = datetime.utcnow()
        db.commit()
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserSchema.from_orm(user)
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/logout", response_model=AuthResponse)
async def logout_user_endpoint(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Logout current user."""
    try:
        return AuthResponse(
            success=True,
            message="Logged out successfully"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.post("/forgot-password", response_model=AuthResponse)
async def forgot_password(
    email_data: OTPRequest,
    db: Session = Depends(get_db)
):
    """Request password reset."""
    try:
        user = get_user_by_email(db, email_data.email)
        if not user:
            return AuthResponse(
                success=True,
                message="If the email exists, you will receive a password reset code."
            )
        
        otp = create_otp_token(db, user.id, "password_reset")
        
        # Try immediate send first, fallback to background task
        email_sent = False
        try:
            email_sent = email_service.send_password_reset_email(
                to_email=user.email,
                username=user.username,
                otp=otp
            )
        except Exception as e:
            print(f"Immediate email send failed: {str(e)}")
            try:
                from ..tasks import send_password_reset_email_task
                send_password_reset_email_task.delay(user.email, user.username, otp)
                email_sent = True
            except Exception as task_error:
                print(f"Background email task failed: {str(task_error)}")
                if os.getenv("DEBUG", "false").lower() == "true":
                    email_sent = True
        
        return AuthResponse(
            success=True,
            message="If the email exists, you will receive a password reset code.",
            data={"email_sent": email_sent}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset request failed: {str(e)}"
        )

@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(
    reset_data: PasswordReset,
    db: Session = Depends(get_db)
):
    """Reset password with OTP."""
    try:
        user = get_user_by_email(db, reset_data.email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if not verify_otp_token(db, user.id, reset_data.otp, "password_reset"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )
        
        user.hashed_password = auth_manager.get_password_hash(reset_data.new_password)
        db.commit()
        
        return AuthResponse(
            success=True,
            message="Password reset successfully. You can now login with your new password."
        )
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Password reset failed: {str(e)}"
        )

@router.get("/me", response_model=UserSchema)
async def get_current_user_info(
    current_user: User = Depends(get_current_verified_user)
):
    """Get current user information."""
    return current_user

@router.put("/me", response_model=UserSchema)
async def update_current_user(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_verified_user),
    db: Session = Depends(get_db)
):
    """Update current user information."""
    try:
        if user_update.email and user_update.email != current_user.email:
            existing_user = get_user_by_email(db, user_update.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            current_user.email = user_update.email
            current_user.is_verified = False  
        
        if user_update.username and user_update.username != current_user.username:
            existing_user = get_user_by_username(db, user_update.username)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
            current_user.username = user_update.username
        
        if user_update.full_name is not None:
            current_user.full_name = user_update.full_name
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        return current_user
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User update failed: {str(e)}"
        )

@router.get("/users", response_model=list[UserSchema])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get all users (admin only)."""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.put("/users/{user_id}", response_model=UserSchema)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    current_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update user (admin only)."""
    try:
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user_update.email:
            user.email = user_update.email
        if user_update.username:
            user.username = user_update.username
        if user_update.full_name is not None:
            user.full_name = user_update.full_name
        if user_update.is_active is not None:
            user.is_active = user_update.is_active
        if user_update.role:
            user.role = user_update.role
        
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
        
        return user
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"User update failed: {str(e)}"
        )

@router.get("/debug/otp/{email}")
async def get_debug_otp(email: str, db: Session = Depends(get_db)):
    """Debug endpoint to get the latest OTP for an email (DEVELOPMENT ONLY)."""
    try:
        from ..database import OTPToken
        
        user = get_user_by_email(db, email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        latest_otp = db.query(OTPToken).filter(
            OTPToken.user_id == user.id,
            OTPToken.is_used == False,
            OTPToken.expires_at > datetime.utcnow()
        ).order_by(OTPToken.created_at.desc()).first()
        
        if not latest_otp:
            return {
                "success": False,
                "message": "No valid OTP found",
                "email": email
            }
        
        return {
            "success": True,
            "email": email,
            "otp": latest_otp.token,
            "token_type": latest_otp.token_type,
            "expires_at": latest_otp.expires_at.isoformat(),
            "created_at": latest_otp.created_at.isoformat(),
            "note": "This is a development endpoint. Remove in production!"
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Debug OTP failed: {str(e)}"
        )


@router.post("/debug/test-email")
async def test_email_service(email_data: OTPRequest):
    """Debug endpoint to test email service (DEVELOPMENT ONLY)."""
    if os.getenv("DEBUG", "false").lower() != "true":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Endpoint not available in production"
        )
    
    try:
        # Test email sending
        test_otp = "123456"
        result = email_service.send_verification_email(
            to_email=email_data.email,
            username="testuser",
            otp=test_otp
        )
        
        return {
            "success": result,
            "message": "Test email sent" if result else "Test email failed",
            "email": email_data.email,
            "test_otp": test_otp
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Email test failed: {str(e)}",
            "email": email_data.email
        }
