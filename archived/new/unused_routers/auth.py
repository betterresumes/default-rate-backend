"""
Unified Authentication API Router with custom endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db, User, Organization
from ..schemas import UserWithOrganization, UserRead, UserCreateFastAPIUsers
from ..auth import (
    get_current_active_user as current_active_user, 
    get_current_verified_user as current_verified_user,
    get_admin_user as require_global_admin, 
    get_admin_user as require_super_admin,
    create_access_token, authenticate_user, create_user
)

# Create unified auth router
router = APIRouter(prefix="/v1/auth", tags=["🔐 Authentication"])

# ========================================
# FASTAPI-USERS STANDARD ENDPOINTS (DISABLED - Using custom endpoints below)
# ========================================

# TODO: Fix FastAPI-Users integration later
# JWT Authentication endpoints
# jwt_router = auth_users.get_auth_router(auth_backend)
# router.include_router(jwt_router, prefix="/jwt", tags=["🔐 JWT Authentication"])

# User registration endpoint  
# register_router = auth_users.get_register_router(UserWithOrganization, UserWithOrganization)
# router.include_router(register_router, prefix="", tags=["📝 User Registration"])

# Email verification endpoints
# verify_router = auth_users.get_verify_router(UserRead)
# router.include_router(verify_router, prefix="", tags=["✉️ Email Verification"])

# Password reset endpoints
# reset_password_router = auth_users.get_reset_password_router()
# router.include_router(reset_password_router, prefix="", tags=["🔑 Password Reset"])

# User management endpoints
# users_router = auth_users.get_users_router(UserRead, UserWithOrganization)
# router.include_router(users_router, prefix="/users", tags=["👤 User Management"])ration endpoint  
register_router = auth_users.get_register_router(UserRead, UserCreateFastAPIUsers)
router.include_router(
    register_router,
    prefix="",
    tags=["📝 User Registration"]
)stAPI-Users integration with multi-tenant organization support
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db, User, Organization
from ..schemas import UserWithOrganization, UserRead, UserCreateFastAPIUsers
from ..auth import (
    get_current_active_user as current_active_user, 
    get_current_verified_user as current_verified_user,
    get_admin_user as require_global_admin, 
    get_admin_user as require_super_admin,
    create_access_token, authenticate_user, create_user
)

# Create unified auth router
router = APIRouter(prefix="/v1/auth", tags=["🔐 Authentication"])

# ========================================
# FASTAPI-USERS STANDARD ENDPOINTS
# ========================================

# JWT Authentication endpoints
jwt_router = auth_users.get_auth_router(auth_backend)
router.include_router(
    jwt_router,
    prefix="/jwt", 
    tags=["🔐 JWT Authentication"]
)

# User registration endpoint  
register_router = auth_users.get_register_router(UserWithOrganization, UserWithOrganization)
router.include_router(
    register_router,
    prefix="",
    tags=["� User Registration"]
)

# Email verification endpoints
verify_router = auth_users.get_verify_router(UserRead)
router.include_router(
    verify_router,
    prefix="",
    tags=["✉️ Email Verification"]
)

# Password reset endpoints
reset_password_router = auth_users.get_reset_password_router()
router.include_router(
    reset_password_router,
    prefix="",
    tags=["🔑 Password Reset"]
)

# User management endpoints
users_router = auth_users.get_users_router(UserRead, UserWithOrganization)
router.include_router(
    users_router,
    prefix="/users",
    tags=["👤 User Management"]
)

# ========================================
# CUSTOM WORKING ENDPOINTS (Due to FastAPI-Users async issues)
# ========================================

@router.post("/login",
           summary="User Login",
           description="Login with email/username and password to get JWT token",
           tags=["🔐 JWT Authentication"])
async def login_user(
    credentials: dict,
    db: Session = Depends(get_db)
):
    """Login user and return JWT token"""
    try:
        email = credentials.get("email") or credentials.get("username")
        password = credentials.get("password")
        
        if not email or not password:
            return {
                "success": False,
                "error": "Missing credentials",
                "message": "Email/username and password are required"
            }
        
        # Get user from database
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return {
                "success": False,
                "error": "Invalid credentials",
                "message": "Invalid email or password"
            }
        
        # Verify password
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        if not pwd_context.verify(password, user.hashed_password):
            return {
                "success": False,
                "error": "Invalid credentials", 
                "message": "Invalid email or password"
            }
        
        # Check if user is active
        if not user.is_active:
            return {
                "success": False,
                "error": "Account disabled",
                "message": "Your account has been disabled. Please contact support."
            }
        
        # Generate JWT token (simplified)
        import jwt
        from datetime import datetime, timedelta
        
        payload = {
            "user_id": str(user.id),
            "email": user.email,
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        SECRET_KEY = "your-secret-key-here"  # In production, use environment variable
        token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return {
            "success": True,
            "message": "Login successful",
            "data": {
                "access_token": token,
                "token_type": "bearer",
                "expires_in": 86400,  # 24 hours
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
                    "last_login": user.last_login.isoformat()
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "Login failed",
            "message": "Unable to login. Please try again.",
            "details": str(e)
        }

@router.post("/register-simple",
           summary="Simple User Registration",
           description="Register new user with standardized response (working alternative to FastAPI-Users)",
           tags=["📝 User Registration"])
async def register_simple(
    user_data: dict,
    db: Session = Depends(get_db)
):
    """Simple user registration that works reliably"""
    try:
        # Validate required fields
        required_fields = ["email", "username", "password"]
        for field in required_fields:
            if not user_data.get(field):
                return {
                    "success": False,
                    "error": "Missing required field",
                    "message": f"{field.title()} is required"
                }
        
        email = user_data["email"]
        username = user_data["username"]
        password = user_data["password"]
        full_name = user_data.get("full_name")
        
        # Check if user already exists
        existing_user_email = db.query(User).filter(User.email == email).first()
        if existing_user_email:
            return {
                "success": False,
                "error": "Email already registered",
                "message": "A user with this email address already exists. Please use a different email or try logging in."
            }
        
        existing_user_username = db.query(User).filter(User.username == username).first()
        if existing_user_username:
            return {
                "success": False,
                "error": "Username already taken",
                "message": "This username is already taken. Please choose a different username."
            }
        
        # Validate password
        if len(password) < 8:
            return {
                "success": False,
                "error": "Password too short",
                "message": "Password must be at least 8 characters long"
            }
        
        # Create user
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash(password)
        
        new_user = User(
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=True,
            is_verified=False,
            global_role="user",
            organization_role="user"
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "success": True,
            "message": "User registered successfully",
            "data": {
                "id": str(new_user.id),
                "email": new_user.email,
                "username": new_user.username,
                "full_name": new_user.full_name,
                "organization_id": None,
                "organization_role": new_user.organization_role,
                "global_role": new_user.global_role,
                "is_active": new_user.is_active,
                "is_verified": new_user.is_verified,
                "created_at": new_user.created_at.isoformat(),
                "updated_at": new_user.updated_at.isoformat()
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": "Registration failed",
            "message": "Unable to create account. Please try again later.",
            "details": str(e)
        }

# ========================================
# CUSTOM MULTI-TENANT ENDPOINTS
# ========================================

@router.get("/me/context",
           summary="Get User Context", 
           description="Get user permissions, roles, and organization context for frontend",
           tags=["👤 Multi-Tenant Context"])
async def get_user_context(
    context = Depends(get_user_organization_context)
):
    """Get user context for frontend (permissions, organization, etc.)"""
    return {
        "success": True,
        "message": "User context retrieved successfully",
        "data": {
            "user_id": str(context["user"].id),
            "email": context["user"].email,
            "username": context["user"].username,
            "full_name": context["user"].full_name,
            "organization_id": str(context["organization_id"]) if context["organization_id"] else None,
            "global_role": context["global_role"],
            "organization_role": context["organization_role"],
            "permissions": {
                "can_see_global": context["can_see_global"],
                "can_see_organization": context["can_see_organization"],
                "can_see_personal": context["can_see_personal"],
                "can_create_organizations": context["global_role"] in ["admin", "super_admin"],
                "can_manage_users": context["global_role"] in ["admin", "super_admin"],
                "can_invite_users": context["organization_role"] == "admin",
                "is_super_admin": context["global_role"] == "super_admin"
            }
        }
    }

@router.get("/me/organizations",
           summary="Get User Organizations",
           description="List organizations the user belongs to or has access to",
           tags=["👤 Multi-Tenant Context"])
async def get_user_organizations(
    user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get organizations user belongs to or has access to"""
    try:
        organizations = []
        
        if user.organization_id:
            # Get user's current organization
            org = db.query(Organization).filter(
                Organization.id == user.organization_id
            ).first()
            if org:
                organizations.append({
                    "id": str(org.id),
                    "name": org.name,
                    "description": org.description,
                    "role": user.organization_role,
                    "is_current": True
                })
        
        # If super admin, can see all organizations
        if user.global_role == "super_admin":
            all_orgs = db.query(Organization).all()
            for org in all_orgs:
                if not user.organization_id or org.id != user.organization_id:
                    organizations.append({
                        "id": str(org.id),
                        "name": org.name,
                        "description": org.description,
                        "role": "super_admin",
                        "is_current": False
                    })
        
        return {
            "success": True,
            "message": "Organizations retrieved successfully",
            "data": organizations
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving organizations: {str(e)}"
        )

# ========================================
# ADMIN MANAGEMENT ENDPOINTS
# ========================================

@router.get("/admin/users", 
           dependencies=[Depends(require_global_admin)],
           summary="List All Users",
           description="Get paginated list of all users with search and filtering (admin only)",
           tags=["🛡️ Admin Management"])
async def list_users(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    organization_id: Optional[str] = None,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_global_admin)
):
    """List users (admin only)"""
    try:
        query = db.query(User)
        
        # Search filter
        if search:
            query = query.filter(
                User.email.ilike(f"%{search}%") |
                User.username.ilike(f"%{search}%") |
                User.full_name.ilike(f"%{search}%")
            )
        
        # Organization filter
        if organization_id:
            query = query.filter(User.organization_id == organization_id)
        
        # Pagination
        offset = (page - 1) * limit
        users = query.offset(offset).limit(limit).all()
        total = query.count()
        
        return {
            "success": True,
            "message": "Users retrieved successfully",
            "data": [
                {
                    "id": str(user.id),
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "organization_id": str(user.organization_id) if user.organization_id else None,
                    "global_role": user.global_role,
                    "organization_role": user.organization_role,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "created_at": user.created_at.isoformat(),
                    "last_login": user.last_login.isoformat() if user.last_login else None
                }
                for user in users
            ],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing users: {str(e)}"
        )

@router.put("/admin/users/{user_id}/role", 
           dependencies=[Depends(require_super_admin)],
           summary="Update User Global Role",
           description="Update a user's global role: user, admin, or super_admin (super admin only)",
           tags=["🛡️ Admin Management"])
async def update_user_global_role(
    user_id: str,
    role_data: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    """Update user global role (super admin only)"""
    try:
        global_role = role_data.get("global_role")
        if global_role not in ["user", "admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid global role. Must be 'user', 'admin', or 'super_admin'"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.global_role = global_role
        db.commit()
        
        return {
            "success": True,
            "message": f"User global role updated to {global_role}",
            "data": {
                "user_id": str(user.id),
                "email": user.email,
                "global_role": user.global_role
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user role: {str(e)}"
        )

@router.put("/admin/users/{user_id}/status", 
           dependencies=[Depends(require_global_admin)],
           summary="Activate/Deactivate User",
           description="Activate or deactivate a user account (admin only)",
           tags=["🛡️ Admin Management"])
async def update_user_status(
    user_id: str,
    status_data: dict,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_global_admin)
):
    """Activate/deactivate user (admin only)"""
    try:
        is_active = status_data.get("is_active")
        if is_active is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="is_active field is required"
            )
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.is_active = is_active
        db.commit()
        
        status_text = "activated" if is_active else "deactivated"
        return {
            "success": True,
            "message": f"User {status_text} successfully",
            "data": {
                "user_id": str(user.id),
                "email": user.email,
                "is_active": user.is_active
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user status: {str(e)}"
        )

# ========================================
# SYSTEM HEALTH ENDPOINTS
# ========================================

@router.get("/status",
           summary="Authentication System Status",
           description="Check authentication system health and available features",
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
                "fastapi_users_integration": True
            }
        }
    }
