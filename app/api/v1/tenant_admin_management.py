from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import uuid
from typing import Optional

from ...core.database import get_db, User, Tenant, Organization
from ...schemas.schemas import UserCreate, UserResponse
from .auth_multi_tenant import get_current_active_user, AuthManager
from .auth_admin import require_super_admin
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/tenant-admin", tags=["Tenant Admin Management"])

# =============================================
# SCHEMAS FOR TENANT ADMIN MANAGEMENT
# =============================================

class TenantWithAdminCreate(BaseModel):
    """Schema for creating tenant with admin user in one operation."""
    # Tenant details
    tenant_name: str
    tenant_description: Optional[str] = None
    tenant_domain: Optional[str] = None
    
    # Admin user details
    admin_email: EmailStr
    admin_password: str
    admin_first_name: str
    admin_last_name: str
    admin_username: Optional[str] = None
    
    # Optional: Create default organization
    create_default_org: bool = True
    default_org_name: Optional[str] = None
    default_org_description: Optional[str] = None

class TenantWithAdminResponse(BaseModel):
    """Response schema for tenant creation with admin."""
    # Tenant info
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    tenant_domain: Optional[str]
    tenant_created_at: datetime
    
    # Admin user info
    admin_user_id: str
    admin_email: str
    admin_full_name: str
    admin_username: str
    admin_created_at: datetime
    
    # Default organization info (if created)
    default_org_id: Optional[str] = None
    default_org_name: Optional[str] = None
    default_org_join_token: Optional[str] = None
    
    # Summary
    success: bool
    message: str

class ExistingUserTenantAssignment(BaseModel):
    """Schema for assigning existing user as tenant admin."""
    user_email: EmailStr
    tenant_id: str

class ExistingUserTenantResponse(BaseModel):
    """Response for existing user tenant assignment."""
    user_id: str
    user_email: str
    tenant_id: str
    tenant_name: str
    previous_role: str
    new_role: str
    success: bool
    message: str

class AssignUserToOrgRequest(BaseModel):
    """Schema for assigning user to organization."""
    user_email: EmailStr
    organization_id: str
    role: str = "member"  # member, org_admin
    
class AssignUserToOrgResponse(BaseModel):
    """Response schema for user organization assignment."""
    success: bool
    message: str
    user_id: str
    user_email: str
    organization_name: str
    assigned_role: str
    tenant_name: str

# =============================================
# TENANT ADMIN MANAGEMENT ENDPOINTS
# =============================================

@router.post("/create-tenant-with-admin", response_model=TenantWithAdminResponse)
async def create_tenant_with_admin(
    tenant_data: TenantWithAdminCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    🎯 SOLUTION 1: Create tenant and assign admin user in ONE atomic operation.
    
    This is the BETTER approach - everything happens in one transaction.
    """
    
    # Check if admin email already exists
    existing_user = db.query(User).filter(User.email == tenant_data.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email {tenant_data.admin_email} already exists. Use the 'assign-existing-user' endpoint instead."
        )
    
    # Check if tenant name already exists
    existing_tenant = db.query(Tenant).filter(Tenant.name == tenant_data.tenant_name).first()
    if existing_tenant:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tenant with name '{tenant_data.tenant_name}' already exists"
        )
    
    try:
        # 1. Create the tenant
        from ...utils.tenant_utils import create_tenant_slug
        
        tenant_slug = create_tenant_slug(tenant_data.tenant_name)
        new_tenant = Tenant(
            id=uuid.uuid4(),
            name=tenant_data.tenant_name,
            slug=tenant_slug,
            description=tenant_data.tenant_description,
            domain=tenant_data.tenant_domain,
            is_active=True,
            created_by=current_user.id,
            created_at=datetime.utcnow()
        )
        
        db.add(new_tenant)
        db.flush()  # Get the tenant ID without committing
        
        # 2. Create the admin user
        # Handle username
        username = tenant_data.admin_username or tenant_data.admin_email.split("@")[0]
        
        # Sanitize username
        import re
        username = re.sub(r'[^a-zA-Z0-9_-]', '_', username)
        if not username or len(username) < 2:
            username = "admin"
        
        # Check username availability and auto-generate if needed
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
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
                    detail="Unable to generate unique username. Please provide custom username."
                )
        
        # Create admin user
        hashed_password = AuthManager.get_password_hash(tenant_data.admin_password)
        full_name = f"{tenant_data.admin_first_name} {tenant_data.admin_last_name}".strip()
        
        admin_user = User(
            id=uuid.uuid4(),
            email=tenant_data.admin_email,
            username=username,
            full_name=full_name,
            hashed_password=hashed_password,
            global_role="tenant_admin",  # Assign tenant admin role
            organization_role=None,  # Will be set when joining organization
            tenant_id=new_tenant.id,  # Assign to the new tenant
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.add(admin_user)
        db.flush()  # Get the user ID without committing
        
        # 3. Create default organization (if requested)
        default_org = None
        if tenant_data.create_default_org:
            from ...utils.tenant_utils import generate_join_token
            
            org_name = tenant_data.default_org_name or f"{tenant_data.tenant_name} - Main Organization"
            org_description = tenant_data.default_org_description or f"Main organization for {tenant_data.tenant_name}"
            
            default_org = Organization(
                id=uuid.uuid4(),
                name=org_name,
                description=org_description,
                tenant_id=new_tenant.id,
                slug=create_tenant_slug(org_name),  # Reuse slug function
                join_token=generate_join_token(),
                default_role="member",
                is_active=True,
                join_enabled=True,
                created_by=admin_user.id,
                created_at=datetime.utcnow()
            )
            
            db.add(default_org)
            db.flush()
            
            # Make admin user the organization admin
            admin_user.organization_id = default_org.id
            admin_user.organization_role = "admin"
        
        # 4. Commit all changes
        db.commit()
        db.refresh(new_tenant)
        db.refresh(admin_user)
        if default_org:
            db.refresh(default_org)
        
        # 5. Prepare response
        return TenantWithAdminResponse(
            tenant_id=str(new_tenant.id),
            tenant_name=new_tenant.name,
            tenant_slug=new_tenant.slug,
            tenant_domain=new_tenant.domain,
            tenant_created_at=new_tenant.created_at,
            
            admin_user_id=str(admin_user.id),
            admin_email=admin_user.email,
            admin_full_name=admin_user.full_name,
            admin_username=admin_user.username,
            admin_created_at=admin_user.created_at,
            
            default_org_id=str(default_org.id) if default_org else None,
            default_org_name=default_org.name if default_org else None,
            default_org_join_token=default_org.join_token if default_org else None,
            
            success=True,
            message=f"Successfully created tenant '{tenant_data.tenant_name}' with admin user '{tenant_data.admin_email}'"
        )
        
    except Exception as e:
        db.rollback()
        
        # Log the error
        import logging
        logging.error(f"Tenant creation with admin failed: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create tenant with admin: {str(e)[:200]}..."
        )

@router.post("/assign-existing-user", response_model=ExistingUserTenantResponse)
async def assign_existing_user_as_tenant_admin(
    assignment_data: ExistingUserTenantAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    🎯 SOLUTION 2: Assign existing user as tenant admin.
    
    Use this when you already have a user and want to make them tenant admin.
    """
    
    # Find the user
    user = db.query(User).filter(User.email == assignment_data.user_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {assignment_data.user_email} not found"
        )
    
    # Find the tenant
    tenant = db.query(Tenant).filter(Tenant.id == assignment_data.tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant with ID {assignment_data.tenant_id} not found"
        )
    
    # Check if user is already a tenant admin of another tenant
    if user.global_role == "tenant_admin" and user.tenant_id != assignment_data.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User is already tenant admin of another tenant. Use super admin to reassign."
        )
    
    try:
        # Store previous role for response
        previous_role = user.global_role
        
        # Update user role and tenant assignment
        user.global_role = "tenant_admin"
        user.tenant_id = assignment_data.tenant_id
        user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(user)
        
        return ExistingUserTenantResponse(
            user_id=str(user.id),
            user_email=user.email,
            tenant_id=str(tenant.id),
            tenant_name=tenant.name,
            previous_role=previous_role,
            new_role=user.global_role,
            success=True,
            message=f"Successfully assigned {user.email} as tenant admin for {tenant.name}"
        )
        
    except Exception as e:
        db.rollback()
        
        import logging
        logging.error(f"User tenant assignment failed: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign user as tenant admin: {str(e)[:200]}..."
        )

@router.get("/tenant/{tenant_id}/admin-info")
async def get_tenant_admin_info(
    tenant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Get information about tenant admin users."""
    
    # Find tenant
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found"
        )
    
    # Find all tenant admins for this tenant
    tenant_admins = db.query(User).filter(
        and_(
            User.tenant_id == tenant_id,
            User.global_role == "tenant_admin"
        )
    ).all()
    
    # Get organizations in this tenant
    organizations = db.query(Organization).filter(Organization.tenant_id == tenant_id).all()
    
    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "tenant_admins": [
            {
                "user_id": str(admin.id),
                "email": admin.email,
                "full_name": admin.full_name,
                "username": admin.username,
                "organization_id": str(admin.organization_id) if admin.organization_id else None,
                "organization_role": admin.organization_role,
                "created_at": admin.created_at,
                "last_login": admin.last_login
            }
            for admin in tenant_admins
        ],
        "organizations_count": len(organizations),
        "organizations": [
            {
                "id": str(org.id),
                "name": org.name,
                "slug": org.slug,
                "is_active": org.is_active
            }
            for org in organizations
        ]
    }

@router.delete("/remove-tenant-admin/{user_id}")
async def remove_tenant_admin_role(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Remove tenant admin role from user (demote to regular user)."""
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if user.global_role != "tenant_admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not a tenant admin"
        )
    
    try:
        # Store info for response
        old_tenant_id = user.tenant_id
        tenant = db.query(Tenant).filter(Tenant.id == old_tenant_id).first() if old_tenant_id else None
        
        # Demote user
        user.global_role = "user"
        user.tenant_id = None  # Remove tenant assignment
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Successfully removed tenant admin role from {user.email}",
            "user_id": str(user.id),
            "user_email": user.email,
            "previous_tenant": tenant.name if tenant else "Unknown",
            "new_role": "user"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove tenant admin role: {str(e)}"
        )

@router.post("/assign-user-to-organization", response_model=AssignUserToOrgResponse)
async def assign_user_to_organization(
    assignment: AssignUserToOrgRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """
    Assign any user to any organization with specified role.
    
    **Super Admin Only** - Direct assignment without join tokens.
    
    Roles:
    - member: Regular organization member
    - org_admin: Organization administrator
    """
    try:
        # Find user by email
        user = db.query(User).filter(User.email == assignment.user_email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email {assignment.user_email} not found"
            )
        
        # Find organization
        organization = db.query(Organization).filter(
            Organization.id == assignment.organization_id
        ).first()
        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with ID {assignment.organization_id} not found"
            )
        
        # Get tenant for context
        tenant = db.query(Tenant).filter(Tenant.id == organization.tenant_id).first()
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization's tenant not found"
            )
        
        # Validate role
        valid_roles = ["member", "org_admin"]
        if assignment.role not in valid_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role. Must be one of: {valid_roles}"
            )
        
        # Check if user is already in this organization
        if user.organization_id == organization.id:
            # Update role if different
            if user.role != assignment.role:
                user.role = assignment.role
                user.updated_at = datetime.utcnow()
                db.commit()
                
                return AssignUserToOrgResponse(
                    success=True,
                    message=f"Updated {user.email} role to {assignment.role} in {organization.name}",
                    user_id=str(user.id),
                    user_email=user.email,
                    organization_name=organization.name,
                    assigned_role=assignment.role,
                    tenant_name=tenant.name
                )
            else:
                return AssignUserToOrgResponse(
                    success=True,
                    message=f"{user.email} is already {assignment.role} in {organization.name}",
                    user_id=str(user.id),
                    user_email=user.email,
                    organization_name=organization.name,
                    assigned_role=assignment.role,
                    tenant_name=tenant.name
                )
        
        # Check if user is in a different organization
        if user.organization_id and user.organization_id != organization.id:
            current_org = db.query(Organization).filter(
                Organization.id == user.organization_id
            ).first()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User {user.email} is already a member of organization '{current_org.name if current_org else 'Unknown'}'. Remove them first or use force update."
            )
        
        # Assign user to organization
        user.organization_id = organization.id
        user.tenant_id = organization.tenant_id
        user.role = assignment.role
        user.updated_at = datetime.utcnow()
        
        # Set appropriate global role based on org role
        if assignment.role == "org_admin":
            user.global_role = "org_admin"
        else:
            user.global_role = "member"
        
        db.commit()
        
        return AssignUserToOrgResponse(
            success=True,
            message=f"Successfully assigned {user.email} as {assignment.role} to {organization.name}",
            user_id=str(user.id),
            user_email=user.email,
            organization_name=organization.name,
            assigned_role=assignment.role,
            tenant_name=tenant.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign user to organization: {str(e)}"
        )
