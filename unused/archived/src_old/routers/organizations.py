"""
Organization Management API Routes
Multi-tenant organization management with invitations and user management
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional
import uuid
from datetime import datetime, timedelta

from ..database import get_db, User, Organization, Invitation, PendingMember
from ..schemas import (
    OrganizationCreate, OrganizationUpdate, OrganizationResponse,
    InvitationCreate, InvitationResponse, UserInOrganization,
    OrganizationCodeResponse, RegenerateCodeResponse, 
    PendingMemberResponse, PendingMemberAction, PendingMemberActionResponse
)
from ..org_code_manager import OrganizationCodeManager
from ..auth import (
    get_current_active_user as current_active_user, 
    get_current_verified_user as current_verified_user,
    get_admin_user as require_global_admin, 
    get_super_admin_user as require_super_admin,
    allow_organization_creation,
    get_user_organization_context
)
from ..email_service import EmailService

router = APIRouter(prefix="/v1/organizations", tags=["🏢 Organizations"])

# Organization Management
@router.post("/", 
             response_model=OrganizationResponse,
             summary="Create New Organization",
             description="Create a new organization (any verified user can create)",
             tags=["🏢 Organization Management"])
async def create_organization(
    org_data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_organization_creation)
):
    """Create a new organization - creator becomes admin of the organization"""
    try:
        # Check if organization name already exists
        existing_org = db.query(Organization).filter(
            Organization.name == org_data.name
        ).first()
        
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name already exists"
            )
        
        # Generate slug from name (simplified version)
        import re
        slug = re.sub(r'[^a-zA-Z0-9-]', '-', org_data.name.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        
        # Make sure slug is unique
        counter = 1
        original_slug = slug
        while db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        # Generate organization code
        org_code = OrganizationCodeManager.generate_code(db)
        
        # Create new organization
        new_org = Organization(
            id=str(uuid.uuid4()),
            name=org_data.name,
            slug=slug,
            description=org_data.description,
            organization_code=org_code,
            code_enabled=True,
            created_by=current_user.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_org)
        db.flush()  # Get the org ID without committing yet
        
        # Update the current user to be admin of this new organization
        current_user.organization_id = new_org.id
        current_user.organization_role = "admin"
        current_user.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(new_org)
        
        return OrganizationResponse(
            id=str(new_org.id),
            name=new_org.name,
            description=new_org.description,
            settings={},  # Return empty settings for now
            created_by=str(new_org.created_by),
            created_at=new_org.created_at,
            updated_at=new_org.updated_at,
            user_count=1,  # Creator is the first user
            admin_count=1  # Creator is the first admin
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating organization: {str(e)}"
        )

@router.get("/", 
            response_model=List[OrganizationResponse],
            summary="List Organizations",
            description="List organizations (admins see all, users see their own)",
            tags=["🏢 Organization Management"])
async def list_organizations(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """List organizations based on user permissions"""
    try:
        query = db.query(Organization)
        
        # Filter based on user permissions
        if context["global_role"] not in ["admin", "super_admin"]:
            # Regular users can only see their own organization
            if context["organization_id"]:
                query = query.filter(Organization.id == context["organization_id"])
            else:
                return []  # User has no organization
        
        # Search filter
        if search:
            query = query.filter(
                or_(
                    Organization.name.ilike(f"%{search}%"),
                    Organization.description.ilike(f"%{search}%")
                )
            )
        
        # Pagination
        offset = (page - 1) * limit
        organizations = query.offset(offset).limit(limit).all()
        
        # Add user counts
        result = []
        for org in organizations:
            user_count = db.query(User).filter(User.organization_id == org.id).count()
            admin_count = db.query(User).filter(
                and_(
                    User.organization_id == org.id,
                    User.organization_role == "admin"
                )
            ).count()
            
            result.append(OrganizationResponse(
                id=str(org.id),
                name=org.name,
                description=org.description,
                settings={},  # Organization model doesn't have settings field yet
                created_by=str(org.created_by),
                created_at=org.created_at,
                updated_at=org.updated_at,
                user_count=user_count,
                admin_count=admin_count
            ))
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing organizations: {str(e)}"
        )

@router.get("/{organization_id}",
            response_model=OrganizationResponse,
            summary="Get Organization Details",
            description="Get detailed organization information",
            tags=["🏢 Organization Management"])
async def get_organization(
    organization_id: str,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """Get organization details"""
    try:
        # Check permissions
        if (context["global_role"] not in ["admin", "super_admin"] and 
            str(context["organization_id"]) != organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this organization"
            )
        
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Get user counts
        user_count = db.query(User).filter(User.organization_id == org.id).count()
        admin_count = db.query(User).filter(
            and_(
                User.organization_id == org.id,
                User.organization_role == "admin"
            )
        ).count()
        
        return OrganizationResponse(
            id=str(org.id),
            name=org.name,
            description=org.description,
            settings={},  # Organization model doesn't have settings field yet
            created_by=str(org.created_by),
            created_at=org.created_at,
            updated_at=org.updated_at,
            user_count=user_count,
            admin_count=admin_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving organization: {str(e)}"
        )

@router.put("/{organization_id}",
            response_model=OrganizationResponse,
            summary="Update Organization",
            description="Update organization details (organization admin or global admin only)",
            tags=["🏢 Organization Management"])
async def update_organization(
    organization_id: str,
    org_data: OrganizationUpdate,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """Update organization (organization admin or global admin only)"""
    try:
        # Check permissions  
        can_update = (
            context["global_role"] in ["admin", "super_admin"] or
            (str(context["organization_id"]) == organization_id and 
             context["organization_role"] == "admin")
        )
        
        if not can_update:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to update this organization"
            )
        
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Update fields
        if org_data.name is not None:
            # Check name uniqueness
            existing = db.query(Organization).filter(
                and_(
                    Organization.name == org_data.name,
                    Organization.id != organization_id
                )
            ).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization name already exists"
                )
            org.name = org_data.name
        
        if org_data.description is not None:
            org.description = org_data.description
        
        # TODO: Add settings support when Organization model is updated
        # if org_data.settings is not None:
        #     org.settings = org_data.settings
        
        org.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(org)
        
        # Get user counts
        user_count = db.query(User).filter(User.organization_id == org.id).count()
        admin_count = db.query(User).filter(
            and_(
                User.organization_id == org.id,
                User.organization_role == "admin"
            )
        ).count()
        
        return OrganizationResponse(
            id=str(org.id),
            name=org.name,
            description=org.description,
            settings={},  # Organization model doesn't have settings field yet
            created_by=str(org.created_by),
            created_at=org.created_at,
            updated_at=org.updated_at,
            user_count=user_count,
            admin_count=admin_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating organization: {str(e)}"
        )

@router.delete("/{organization_id}",
               summary="Delete Organization",
               description="Delete organization (organization admin or super admin)",
               tags=["🏢 Organization Management"])
async def delete_organization(
    organization_id: str,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """Delete organization (organization admin or super admin)"""
    try:
        # Check permissions - organization admin can delete their own org, super admin can delete any
        can_delete = (
            context["global_role"] == "super_admin" or
            (str(context["organization_id"]) == organization_id and 
             context["organization_role"] == "admin")
        )
        
        if not can_delete:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied. Only organization admins can delete their organization or super admins can delete any organization."
            )
            
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Check if organization has users (excluding the current admin)
        other_users_count = db.query(User).filter(
            and_(
                User.organization_id == organization_id,
                User.id != context["user"].id  # Exclude current user (the admin)
            )
        ).count()
        
        if other_users_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete organization with {other_users_count} other users. Remove all other users first."
            )
        
        # Delete all invitations for this organization
        db.query(Invitation).filter(
            Invitation.organization_id == organization_id
        ).delete()
        
        # Remove the admin user from the organization before deleting
        admin_user = context["user"]
        admin_user.organization_id = None
        admin_user.organization_role = None
        admin_user.updated_at = datetime.utcnow()
        
        # Delete organization
        db.delete(org)
        db.commit()
        
        return {
            "success": True,
            "message": f"Organization '{org.name}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting organization: {str(e)}"
        )

# Organization Users Management
@router.get("/{organization_id}/users",
            response_model=List[UserInOrganization],
            summary="List Organization Users",
            description="List all users in an organization",
            tags=["👥 Organization Users"])
async def list_organization_users(
    organization_id: str,
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """List users in organization"""
    try:
        # Check permissions
        can_view = (
            context["global_role"] in ["admin", "super_admin"] or
            (str(context["organization_id"]) == organization_id and 
             context["organization_role"] == "admin")
        )
        
        if not can_view:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to view organization users"
            )
        
        query = db.query(User).filter(User.organization_id == organization_id)
        
        # Search filter
        if search:
            query = query.filter(
                or_(
                    User.email.ilike(f"%{search}%"),
                    User.username.ilike(f"%{search}%"),
                    User.full_name.ilike(f"%{search}%")
                )
            )
        
        # Pagination
        offset = (page - 1) * limit
        users = query.offset(offset).limit(limit).all()
        
        return [
            UserInOrganization(
                id=str(user.id),
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                organization_role=user.organization_role,
                global_role=user.global_role,
                is_active=user.is_active,
                is_verified=user.is_verified,
                created_at=user.created_at,
                last_login=user.last_login
            )
            for user in users
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing organization users: {str(e)}"
        )

@router.put("/{organization_id}/users/{user_id}/role",
            summary="Update User Organization Role",
            description="Update a user's role within the organization",
            tags=["👥 Organization Users"])
async def update_user_organization_role(
    organization_id: str,
    user_id: str,
    organization_role: str,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """Update user's organization role"""
    try:
        if organization_role not in ["user", "admin"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid organization role. Must be 'user' or 'admin'"
            )
        
        # Check permissions
        can_update = (
            context["global_role"] in ["admin", "super_admin"] or
            (str(context["organization_id"]) == organization_id and 
             context["organization_role"] == "admin")
        )
        
        if not can_update:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to update user roles"
            )
        
        user = db.query(User).filter(
            and_(
                User.id == user_id,
                User.organization_id == organization_id
            )
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this organization"
            )
        
        user.organization_role = organization_role
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"User role updated to {organization_role}",
            "data": {
                "user_id": user.id,
                "email": user.email,
                "organization_role": user.organization_role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating user role: {str(e)}"
        )

@router.delete("/{organization_id}/users/{user_id}",
               summary="Remove User from Organization",
               description="Remove a user from the organization",
               tags=["👥 Organization Users"])
async def remove_user_from_organization(
    organization_id: str,
    user_id: str,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """Remove user from organization"""
    try:
        # Check permissions
        can_remove = (
            context["global_role"] in ["admin", "super_admin"] or
            (str(context["organization_id"]) == organization_id and 
             context["organization_role"] == "admin")
        )
        
        if not can_remove:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to remove users"
            )
        
        user = db.query(User).filter(
            and_(
                User.id == user_id,
                User.organization_id == organization_id
            )
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in this organization"
            )
        
        # Remove user from organization
        user.organization_id = None
        user.organization_role = None
        user.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {
            "success": True,
            "message": f"User {user.email} removed from organization"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error removing user from organization: {str(e)}"
        )

# Organization Invitations
@router.post("/{organization_id}/invitations",
             response_model=InvitationResponse,
             summary="Invite User to Organization",
             description="Send an invitation to join the organization",
             tags=["📧 Organization Invitations"])
async def invite_user_to_organization(
    organization_id: str,
    invitation_data: InvitationCreate,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """Invite user to organization"""
    try:
        # Check permissions
        can_invite = (
            context["global_role"] in ["admin", "super_admin"] or
            (str(context["organization_id"]) == organization_id and 
             context["organization_role"] == "admin")
        )
        
        if not can_invite:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to send invitations"
            )
        
        # Check if organization exists
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )
        
        # Check if user already exists and is in organization
        existing_user = db.query(User).filter(User.email == invitation_data.email).first()
        if existing_user and existing_user.organization_id == organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already a member of this organization"
            )
        
        # Check if invitation already exists
        existing_invitation = db.query(Invitation).filter(
            and_(
                Invitation.email == invitation_data.email,
                Invitation.organization_id == organization_id,
                Invitation.is_used == False  # Use is_used instead of status
            )
        ).first()
        
        if existing_invitation:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation already sent to this email"
            )
        
        # Create invitation
        invitation = Invitation(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            email=invitation_data.email,
            role=invitation_data.organization_role,  # Use 'role' field from database
            invited_by=context["user"].id,
            token=str(uuid.uuid4()),
            expires_at=datetime.utcnow() + timedelta(days=7),  # 7 days expiry
            is_used=False,
            created_at=datetime.utcnow()
        )
        
        db.add(invitation)
        db.commit()
        db.refresh(invitation)
        
        # Send invitation email
        try:
            email_service = EmailService()
            await email_service.send_organization_invitation(
                invitation_data.email,
                org.name,
                context["user"].full_name or context["user"].email,
                invitation.token
            )
        except Exception as e:
            print(f"⚠️ Warning: Failed to send invitation email: {e}")
            # Don't fail the invitation creation if email fails
        
        return InvitationResponse(
            id=str(invitation.id),
            organization_id=str(invitation.organization_id),
            organization_name=org.name,
            email=invitation.email,
            organization_role=invitation.role,  # Map 'role' to 'organization_role'
            invited_by=str(invitation.invited_by),
            status="pending",  # Default status since using is_used boolean
            created_at=invitation.created_at,
            expires_at=invitation.expires_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating invitation: {str(e)}"
        )

@router.get("/{organization_id}/invitations",
            response_model=List[InvitationResponse],
            summary="List Organization Invitations",
            description="List all pending/sent invitations for the organization",
            tags=["📧 Organization Invitations"])
async def list_organization_invitations(
    organization_id: str,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """List organization invitations"""
    try:
        # Check permissions
        can_view = (
            context["global_role"] in ["admin", "super_admin"] or
            (str(context["organization_id"]) == organization_id and 
             context["organization_role"] == "admin")
        )
        
        if not can_view:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to view invitations"
            )
        
        query = db.query(Invitation).filter(
            Invitation.organization_id == organization_id
        )
        
        if status:
            if status == "pending":
                query = query.filter(Invitation.is_used == False)
            elif status == "accepted":
                query = query.filter(Invitation.is_used == True)
            # Note: We could add expired check based on expires_at if needed
        
        invitations = query.order_by(Invitation.created_at.desc()).all()
        
        # Get organization name
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        org_name = org.name if org else "Unknown"
        
        return [
            InvitationResponse(
                id=str(inv.id),
                organization_id=str(inv.organization_id),
                organization_name=org_name,
                email=inv.email,
                organization_role=inv.role,  # Use 'role' field from database
                invited_by=str(inv.invited_by),
                status="accepted" if inv.is_used else "pending",  # Convert is_used to status
                created_at=inv.created_at,
                expires_at=inv.expires_at
            )
            for inv in invitations
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing invitations: {str(e)}"
        )

@router.post("/invitations/{token}/accept",
             summary="Accept Organization Invitation",
             description="Accept an organization invitation using the token",
             tags=["📧 Organization Invitations"])
async def accept_organization_invitation(
    token: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_verified_user)
):
    """Accept organization invitation"""
    try:
        # Find invitation
        invitation = db.query(Invitation).filter(
            and_(
                Invitation.token == token,
                Invitation.status == "pending"
            )
        ).first()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid or expired invitation"
            )
        
        # Check if invitation is expired
        if invitation.expires_at < datetime.utcnow():
            invitation.status = "expired"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invitation has expired"
            )
        
        # Check if user email matches invitation email
        if user.email != invitation.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation is for a different email address"
            )
        
        # Check if user is already in an organization
        if user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already a member of an organization"
            )
        
        # Add user to organization
        user.organization_id = invitation.organization_id
        user.organization_role = invitation.organization_role
        user.updated_at = datetime.utcnow()
        
        # Update invitation status
        invitation.status = "accepted"
        invitation.accepted_at = datetime.utcnow()
        
        db.commit()
        
        # Get organization details
        org = db.query(Organization).filter(Organization.id == invitation.organization_id).first()
        
        return {
            "success": True,
            "message": f"Successfully joined {org.name}",
            "data": {
                "organization_id": org.id,
                "organization_name": org.name,
                "organization_role": user.organization_role
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accepting invitation: {str(e)}"
        )

@router.delete("/invitations/{invitation_id}",
               summary="Cancel Organization Invitation",
               description="Cancel a pending organization invitation",
               tags=["📧 Organization Invitations"])
async def cancel_organization_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    context = Depends(get_user_organization_context)
):
    """Cancel organization invitation"""
    try:
        invitation = db.query(Invitation).filter(
            Invitation.id == invitation_id
        ).first()
        
        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation not found"
            )
        
        # Check permissions
        can_cancel = (
            context["global_role"] in ["admin", "super_admin"] or
            (str(context["organization_id"]) == invitation.organization_id and 
             context["organization_role"] == "admin") or
            invitation.invited_by == context["user"].id
        )
        
        if not can_cancel:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied to cancel this invitation"
            )
        
        if invitation.status != "pending":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel invitation with status: {invitation.status}"
            )
        
        invitation.status = "cancelled"
        db.commit()
        
        return {
            "success": True,
            "message": "Invitation cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cancelling invitation: {str(e)}"
        )

# ========================
# ORGANIZATION CODE MANAGEMENT
# ========================

@router.get("/{organization_id}/code",
            response_model=OrganizationCodeResponse,
            summary="Get Organization Code",
            description="Get organization code for team joining (admin only)",
            tags=["🔑 Organization Codes"])
async def get_organization_code(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """Get organization code for sharing with team members"""
    try:
        # Validate organization access (admin only)
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(404, "Organization not found")
        
        # Check permissions (org admin or super admin)
        if not (current_user.global_role == "super_admin" or 
                (str(current_user.organization_id) == organization_id and 
                 current_user.organization_role == "admin")):
            raise HTTPException(403, "Not authorized to view organization code")
        
        # Get member counts
        members_count = db.query(User).filter(
            User.organization_id == organization_id,
            User.organization_status == "active"
        ).count()
        
        pending_count = db.query(PendingMember).filter(
            PendingMember.organization_id == organization_id,
            PendingMember.status == "pending"
        ).count()
        
        return OrganizationCodeResponse(
            organization_code=org.organization_code,
            code_enabled=org.code_enabled,
            code_created_at=org.code_created_at,
            members_count=members_count,
            pending_members_count=pending_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error getting organization code: {str(e)}")

@router.post("/{organization_id}/code/regenerate",
             response_model=RegenerateCodeResponse,
             summary="Regenerate Organization Code",
             description="Generate new organization code (admin only)",
             tags=["🔑 Organization Codes"])
async def regenerate_organization_code(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """Generate a new organization code (invalidates old one)"""
    try:
        # Validate organization access (admin only)
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(404, "Organization not found")
        
        # Check permissions (org admin or super admin)
        if not (current_user.global_role == "super_admin" or 
                (str(current_user.organization_id) == organization_id and 
                 current_user.organization_role == "admin")):
            raise HTTPException(403, "Not authorized to regenerate organization code")
        
        # Generate new code
        new_code = OrganizationCodeManager.regenerate_code(db, organization_id)
        
        return RegenerateCodeResponse(
            new_code=new_code,
            message="Organization code regenerated successfully",
            code_enabled=org.code_enabled
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error regenerating code: {str(e)}")

@router.post("/{organization_id}/code/toggle",
             summary="Enable/Disable Organization Code",
             description="Enable or disable organization code joining (admin only)",
             tags=["🔑 Organization Codes"])
async def toggle_organization_code(
    organization_id: str,
    enable: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """Enable or disable organization code for joining"""
    try:
        # Validate organization access (admin only)
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(404, "Organization not found")
        
        # Check permissions (org admin or super admin)
        if not (current_user.global_role == "super_admin" or 
                (str(current_user.organization_id) == organization_id and 
                 current_user.organization_role == "admin")):
            raise HTTPException(403, "Not authorized to toggle organization code")
        
        if enable:
            OrganizationCodeManager.enable_code(db, organization_id)
            message = "Organization code enabled"
        else:
            OrganizationCodeManager.disable_code(db, organization_id)
            message = "Organization code disabled"
        
        return {
            "success": True,
            "message": message,
            "code_enabled": enable
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error toggling code: {str(e)}")

# ========================
# PENDING MEMBER MANAGEMENT
# ========================

@router.get("/{organization_id}/pending-members",
            response_model=List[PendingMemberResponse],
            summary="List Pending Members",
            description="List users awaiting admin approval (admin only)",
            tags=["👥 Pending Members"])
async def list_pending_members(
    organization_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """List users who registered with org code but need approval"""
    try:
        # Validate organization access (admin only)
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(404, "Organization not found")
        
        # Check permissions (org admin or super admin)
        if not (current_user.global_role == "super_admin" or 
                (str(current_user.organization_id) == organization_id and 
                 current_user.organization_role == "admin")):
            raise HTTPException(403, "Not authorized to view pending members")
        
        # Get pending members with user details
        pending_members = db.query(PendingMember).join(User).filter(
            PendingMember.organization_id == organization_id,
            PendingMember.status == "pending"
        ).all()
        
        result = []
        for pending in pending_members:
            result.append(PendingMemberResponse(
                id=str(pending.id),
                email=pending.email,
                full_name=pending.user.full_name,
                requested_role=pending.requested_role,
                organization_code_used=pending.organization_code_used,
                status=pending.status,
                requested_at=pending.requested_at,
                user_id=str(pending.user_id)
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error listing pending members: {str(e)}")

@router.post("/{organization_id}/pending-members/{member_id}/action",
             response_model=PendingMemberActionResponse,
             summary="Approve/Reject Pending Member",
             description="Approve or reject user's organization join request (admin only)",
             tags=["👥 Pending Members"])
async def action_pending_member(
    organization_id: str,
    member_id: str,
    action_data: PendingMemberAction,
    db: Session = Depends(get_db),
    current_user: User = Depends(current_active_user)
):
    """Approve or reject pending member"""
    try:
        # Validate organization access (admin only)
        org = db.query(Organization).filter(Organization.id == organization_id).first()
        if not org:
            raise HTTPException(404, "Organization not found")
        
        # Check permissions (org admin or super admin)
        if not (current_user.global_role == "super_admin" or 
                (str(current_user.organization_id) == organization_id and 
                 current_user.organization_role == "admin")):
            raise HTTPException(403, "Not authorized to manage pending members")
        
        # Find pending member
        pending = db.query(PendingMember).filter(
            PendingMember.id == member_id,
            PendingMember.organization_id == organization_id
        ).first()
        
        if not pending:
            raise HTTPException(404, "Pending member not found")
        
        if pending.status != "pending":
            raise HTTPException(400, f"Member already {pending.status}")
        
        # Get the user
        user = db.query(User).filter(User.id == pending.user_id).first()
        if not user:
            raise HTTPException(404, "User not found")
        
        if action_data.action == "approve":
            # Approve user
            user.organization_id = organization_id
            user.organization_role = action_data.role.value if action_data.role else pending.requested_role
            user.organization_status = "active"
            
            pending.status = "approved"
            pending.approved_by = current_user.id
            pending.approved_at = datetime.utcnow()
            
            message = f"User {user.email} approved and added to organization"
            new_status = "approved"
            
        elif action_data.action == "reject":
            # Reject user
            user.organization_id = None
            user.organization_role = "user"
            user.organization_status = "rejected"
            
            pending.status = "rejected"
            pending.approved_by = current_user.id
            pending.approved_at = datetime.utcnow()
            pending.rejection_reason = action_data.rejection_reason
            
            message = f"User {user.email} rejected"
            new_status = "rejected"
        
        else:
            raise HTTPException(400, "Invalid action. Use 'approve' or 'reject'")
        
        db.commit()
        
        return PendingMemberActionResponse(
            success=True,
            message=message,
            member_id=member_id,
            action=action_data.action,
            new_status=new_status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error processing member action: {str(e)}")

# ========================
# SUPER ADMIN ORGANIZATION MANAGEMENT
# ========================

@router.post("/admin/create-organization",
             response_model=OrganizationResponse,
             summary="Create Organization (Super Admin)",
             description="Create organization and assign admin (super admin only)",
             tags=["🔧 Super Admin"])
async def admin_create_organization(
    org_data: OrganizationCreate,
    admin_email: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_super_admin)
):
    """Super admin endpoint to create organization and assign admin"""
    try:
        # Check if admin user exists
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            raise HTTPException(404, f"User with email {admin_email} not found")
        
        if admin_user.organization_id:
            raise HTTPException(400, f"User {admin_email} already belongs to an organization")
        
        # Generate slug and code
        import re
        slug = re.sub(r'[^a-zA-Z0-9-]', '-', org_data.name.lower())
        slug = re.sub(r'-+', '-', slug).strip('-')
        
        counter = 1
        original_slug = slug
        while db.query(Organization).filter(Organization.slug == slug).first():
            slug = f"{original_slug}-{counter}"
            counter += 1
        
        org_code = OrganizationCodeManager.generate_code(db)
        
        # Create organization
        new_org = Organization(
            id=str(uuid.uuid4()),
            name=org_data.name,
            slug=slug,
            description=org_data.description,
            organization_code=org_code,
            code_enabled=True,
            created_by=current_user.id
        )
        
        db.add(new_org)
        db.flush()
        
        # Assign admin
        admin_user.organization_id = new_org.id
        admin_user.organization_role = "admin"
        admin_user.organization_status = "active"
        
        db.commit()
        db.refresh(new_org)
        
        return OrganizationResponse(
            id=str(new_org.id),
            name=new_org.name,
            description=new_org.description,
            settings={"organization_code": org_code},
            created_by=str(new_org.created_by),
            created_at=new_org.created_at,
            updated_at=new_org.updated_at,
            user_count=1,
            admin_count=1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error creating organization: {str(e)}")
