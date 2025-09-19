#!/usr/bin/env python3
"""
Join Link Management System
============================

Simple, production-ready system for organization invitations via shareable links.
No approval workflows, no pending states, no organization codes to remember.

Features:
- Generate secure join links for organizations
- Validate join tokens and auto-join users
- Super admin control over all organizations
- Track join statistics and link usage
"""

import secrets
import string
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from .database import Organization, User


class JoinLinkManager:
    """Manages organization join links and auto-joining logic"""
    
    @staticmethod
    def generate_join_token() -> str:
        """Generate a secure 32-character join token"""
        # Use URL-safe characters: letters + numbers + dashes
        alphabet = string.ascii_letters + string.digits + '-_'
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    @staticmethod
    def create_organization_with_join_link(
        db: Session,
        name: str,
        slug: str,
        created_by: str,
        domain: Optional[str] = None,
        description: Optional[str] = None,
        max_users: int = 100,
        default_role: str = "user"
    ) -> Dict[str, Any]:
        """
        Create a new organization with a join link
        
        Returns:
            {
                "organization": Organization object,
                "join_link": "https://app.yoursite.com/join/abc123...",
                "join_token": "abc123..."
            }
        """
        
        # Generate unique join token
        join_token = JoinLinkManager.generate_join_token()
        
        # Ensure token is unique
        while db.query(Organization).filter(Organization.join_token == join_token).first():
            join_token = JoinLinkManager.generate_join_token()
        
        # Create organization
        organization = Organization(
            name=name,
            slug=slug,
            domain=domain,
            description=description,
            max_users=max_users,
            join_token=join_token,
            join_enabled=True,
            default_role=default_role,
            created_by=created_by
        )
        
        db.add(organization)
        db.commit()
        db.refresh(organization)
        
        return {
            "organization": organization,
            "join_token": join_token,
            "join_link": f"https://app.yoursite.com/join/{join_token}"
        }
    
    @staticmethod
    def regenerate_join_link(
        db: Session,
        organization_id: str,
        regenerated_by: str
    ) -> Dict[str, Any]:
        """
        Regenerate join link for an organization (security purposes)
        """
        organization = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not organization:
            raise ValueError("Organization not found")
        
        # Generate new unique token
        new_token = JoinLinkManager.generate_join_token()
        while db.query(Organization).filter(Organization.join_token == new_token).first():
            new_token = JoinLinkManager.generate_join_token()
        
        # Update organization
        organization.join_token = new_token
        organization.join_created_at = datetime.utcnow()
        
        db.commit()
        db.refresh(organization)
        
        return {
            "organization": organization,
            "join_token": new_token,
            "join_link": f"https://app.yoursite.com/join/{new_token}"
        }
    
    @staticmethod
    def validate_join_token(db: Session, join_token: str) -> Optional[Organization]:
        """
        Validate a join token and return the organization if valid
        """
        organization = db.query(Organization).filter(
            and_(
                Organization.join_token == join_token,
                Organization.join_enabled == True,
                Organization.is_active == True
            )
        ).first()
        
        return organization
    
    @staticmethod
    def join_organization_via_token(
        db: Session,
        user_id: str,
        join_token: str
    ) -> Dict[str, Any]:
        """
        Join a user to an organization via join token
        
        Returns:
            {
                "success": True/False,
                "message": "Success/error message",
                "organization": Organization object (if success),
                "user": Updated User object (if success)
            }
        """
        
        # Get user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"success": False, "message": "User not found"}
        
        # Check if user already in an organization
        if user.organization_id:
            return {
                "success": False, 
                "message": "User already belongs to an organization"
            }
        
        # Validate join token
        organization = JoinLinkManager.validate_join_token(db, join_token)
        if not organization:
            return {
                "success": False,
                "message": "Invalid or expired join link"
            }
        
        # Check organization capacity
        current_users = db.query(User).filter(
            User.organization_id == organization.id
        ).count()
        
        if current_users >= organization.max_users:
            return {
                "success": False,
                "message": f"Organization has reached maximum capacity ({organization.max_users} users)"
            }
        
        # Join user to organization
        user.organization_id = organization.id
        user.organization_role = organization.default_role
        user.joined_via_token = join_token
        
        db.commit()
        db.refresh(user)
        db.refresh(organization)
        
        return {
            "success": True,
            "message": f"Successfully joined {organization.name}",
            "organization": organization,
            "user": user
        }
    
    @staticmethod
    def toggle_join_link(
        db: Session,
        organization_id: str,
        enabled: bool
    ) -> Dict[str, Any]:
        """
        Enable/disable join link for an organization
        """
        organization = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not organization:
            return {"success": False, "message": "Organization not found"}
        
        organization.join_enabled = enabled
        db.commit()
        db.refresh(organization)
        
        status = "enabled" if enabled else "disabled"
        return {
            "success": True,
            "message": f"Join link {status} for {organization.name}",
            "organization": organization
        }
    
    @staticmethod
    def get_organization_join_stats(db: Session, organization_id: str) -> Dict[str, Any]:
        """
        Get join statistics for an organization
        """
        organization = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not organization:
            return {"success": False, "message": "Organization not found"}
        
        # Count users who joined via this token
        users_joined_via_token = db.query(User).filter(
            and_(
                User.organization_id == organization_id,
                User.joined_via_token == organization.join_token
            )
        ).count()
        
        # Total users in organization
        total_users = db.query(User).filter(
            User.organization_id == organization_id
        ).count()
        
        return {
            "success": True,
            "organization_name": organization.name,
            "join_token": organization.join_token,
            "join_enabled": organization.join_enabled,
            "users_joined_via_current_token": users_joined_via_token,
            "total_users": total_users,
            "max_users": organization.max_users,
            "capacity_percentage": round((total_users / organization.max_users) * 100, 1),
            "join_link_created": organization.join_created_at,
            "current_join_link": f"https://app.yoursite.com/join/{organization.join_token}"
        }


class SuperAdminManager:
    """Super admin utilities for managing all organizations"""
    
    @staticmethod
    def create_organization_as_super_admin(
        db: Session,
        super_admin_user_id: str,
        org_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Super admin creates organization and can optionally assign an admin
        """
        
        # Verify super admin
        super_admin = db.query(User).filter(
            and_(
                User.id == super_admin_user_id,
                User.global_role == "super_admin"
            )
        ).first()
        
        if not super_admin:
            return {"success": False, "message": "Only super admins can create organizations"}
        
        # Create organization
        result = JoinLinkManager.create_organization_with_join_link(
            db=db,
            name=org_data["name"],
            slug=org_data["slug"],
            created_by=super_admin_user_id,
            domain=org_data.get("domain"),
            description=org_data.get("description"),
            max_users=org_data.get("max_users", 100),
            default_role=org_data.get("default_role", "user")
        )
        
        organization = result["organization"]
        
        # Optionally assign an admin user
        if "admin_email" in org_data:
            admin_user = db.query(User).filter(User.email == org_data["admin_email"]).first()
            if admin_user and not admin_user.organization_id:
                admin_user.organization_id = organization.id
                admin_user.organization_role = "admin"
                admin_user.joined_via_token = organization.join_token
                db.commit()
                
                result["assigned_admin"] = admin_user
        
        return result
    
    @staticmethod
    def list_all_organizations(db: Session, super_admin_user_id: str) -> Dict[str, Any]:
        """
        Super admin can see all organizations with join stats
        """
        super_admin = db.query(User).filter(
            and_(
                User.id == super_admin_user_id,
                User.global_role == "super_admin"
            )
        ).first()
        
        if not super_admin:
            return {"success": False, "message": "Only super admins can view all organizations"}
        
        organizations = db.query(Organization).all()
        
        org_list = []
        for org in organizations:
            stats = JoinLinkManager.get_organization_join_stats(db, str(org.id))
            if stats["success"]:
                org_list.append({
                    "id": str(org.id),
                    "name": org.name,
                    "slug": org.slug,
                    "is_active": org.is_active,
                    "join_enabled": org.join_enabled,
                    "total_users": stats["total_users"],
                    "max_users": org.max_users,
                    "capacity_percentage": stats["capacity_percentage"],
                    "join_link": stats["current_join_link"],
                    "created_at": org.created_at
                })
        
        return {
            "success": True,
            "organizations": org_list,
            "total_organizations": len(org_list)
        }


# Usage Examples
if __name__ == "__main__":
    """
    EXAMPLE USAGE:
    
    # 1. Super admin creates organization
    result = SuperAdminManager.create_organization_as_super_admin(
        db=db,
        super_admin_user_id="super-admin-uuid",
        org_data={
            "name": "Acme Corp",
            "slug": "acme-corp",
            "domain": "acme.com",
            "description": "Financial analysis team",
            "max_users": 50,
            "admin_email": "admin@acme.com"  # Optional: assign admin
        }
    )
    
    # 2. Get join link to share
    join_link = result["join_link"]
    # "https://app.yoursite.com/join/Kx9mP2nQ8vR4tL7wZ3bH1cF6gJ5uE0sA"
    
    # 3. User clicks link and registers/logs in
    # Frontend gets token from URL: /join/Kx9mP2nQ8vR4tL7wZ3bH1cF6gJ5uE0sA
    
    # 4. User automatically joins organization
    join_result = JoinLinkManager.join_organization_via_token(
        db=db,
        user_id="new-user-uuid",
        join_token="Kx9mP2nQ8vR4tL7wZ3bH1cF6gJ5uE0sA"
    )
    
    # 5. Check organization stats
    stats = JoinLinkManager.get_organization_join_stats(db, org_id)
    """
    pass
