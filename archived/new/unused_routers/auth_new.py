"""
Professional Authentication API Routes
High-performance authentication endpoints with organization support
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Optional

from ..database import get_db, User, Organization
from ..schemas import (
    UserCreate, UserUpdate, UserWithOrganization,
    Token, AuthResponse
)
from ..auth_system import (
    auth_users, current_active_user, current_verified_user,
    require_global_admin, require_super_admin,
    get_user_organization_context, get_data_access_filter,
    get_user_manager, auth_backend, jwt_strategy
)

# Create router with clean organization
router = APIRouter(prefix="/v1/auth")
security = HTTPBearer()

# Use FastAPI-Users routers but with better organization
auth_router = auth_users.get_auth_router(auth_backend)
register_router = auth_users.get_register_router(UserCreate, UserWithOrganization)
verify_router = auth_users.get_verify_router(UserWithOrganization)
reset_password_router = auth_users.get_reset_password_router()

# Include routers with specific tags to avoid duplicates and remove default tags
router.include_router(
    auth_router, 
    prefix="",
    tags=["🔐 Core Authentication"]
)
router.include_router(
    register_router, 
    prefix="",
    tags=["📝 User Registration"]
)
router.include_router(
    verify_router, 
    prefix="",
    tags=["✉️ Email Verification"]
)
router.include_router(
    reset_password_router, 
    prefix="",
    tags=["🔑 Password Reset"]
)

# ONLY custom endpoints that don't conflict with FastAPI-Users

@router.get("/profile", 
           response_model=UserWithOrganization,
           summary="Get Current User Profile",
           description="Retrieve the authenticated user's profile with organization details",
           tags=["👤 User Profile Management"])
async def get_current_user_profile(
    user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Get current user profile with organization details"""
    try:
        # Get organization details if user belongs to one
        organization = None
        if user.organization_id:
            organization = db.query(Organization).filter(
                Organization.id == user.organization_id
            ).first()
        
        return UserWithOrganization(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            organization_id=user.organization_id,
            organization_role=user.organization_role,
            global_role=user.global_role,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login=user.last_login,
            organization=organization
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user profile: {str(e)}"
        )

@router.get("/me/context",
           summary="Get User Context", 
           description="Get user permissions, roles, and organization context for frontend",
           tags=["👤 User Profile Management"])
async def get_user_context(
    context = Depends(get_user_organization_context)
):
    """Get user context for frontend (permissions, organization, etc.)"""
    return {
        "success": True,
        "data": {
            "user_id": context["user"].id,
            "email": context["user"].email,
            "username": context["user"].username,
            "full_name": context["user"].full_name,
            "organization_id": context["organization_id"],
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
           tags=["👤 User Profile Management"])
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
                    "id": org.id,
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
                        "id": org.id,
                        "name": org.name,
                        "description": org.description,
                        "role": "super_admin",
                        "is_current": False
                    })
        
        return {
            "success": True,
            "data": organizations
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving organizations: {str(e)}"
        )

@router.post("/logout",
            summary="Logout User",
            description="Logout the current user and invalidate session",
            tags=["🔐 Core Authentication"])
async def logout_user(
    user: User = Depends(current_active_user)
):
    """Logout current user"""
    # With JWT, logout is handled client-side by removing the token
    # But we can log the logout event
    print(f"🔓 User {user.email} logged out")
    
    return {
        "success": True,
        "message": "Logged out successfully"
    }

@router.get("/status",
           summary="Authentication System Status",
           description="Check authentication system health and available features",
           tags=["⚡ System Health"])
async def auth_status():
    """Check authentication system status"""
    return {
        "success": True,
        "status": "Authentication system operational",
        "features": {
            "jwt_authentication": True,
            "email_verification": True,
            "password_reset": True,
            "organization_support": True,
            "role_based_access": True
        }
    }

@router.patch("/profile/update",
             summary="Update User Profile",
             description="Update user profile information (name, username, etc.)",
             tags=["👤 User Profile Management"])
async def update_user_profile(
    profile_data: dict,
    user: User = Depends(current_verified_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    try:
        # Allow updating specific fields
        allowed_fields = ["full_name", "username"]
        
        for field, value in profile_data.items():
            if field in allowed_fields and hasattr(user, field):
                # Check username uniqueness if updating username
                if field == "username":
                    existing_user = db.query(User).filter(
                        User.username == value,
                        User.id != user.id
                    ).first()
                    if existing_user:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Username already taken"
                        )
                
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return {
            "success": True,
            "message": "Profile updated successfully",
            "data": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating profile: {str(e)}"
        )

# Admin endpoints
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
            "data": [
                {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "full_name": user.full_name,
                    "organization_id": user.organization_id,
                    "global_role": user.global_role,
                    "organization_role": user.organization_role,
                    "is_active": user.is_active,
                    "is_verified": user.is_verified,
                    "created_at": user.created_at,
                    "last_login": user.last_login
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
    global_role: str,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_super_admin)
):
    """Update user global role (super admin only)"""
    try:
        if global_role not in ["user", "admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid global role"
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
                "user_id": user.id,
                "email": user.email,
                "global_role": user.global_role
            }
        }
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
    is_active: bool,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_global_admin)
):
    """Activate/deactivate user (admin only)"""
    try:
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
                "user_id": user.id,
                "email": user.email,
                "is_active": user.is_active
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user status: {str(e)}"
        )

# Include the user management router


