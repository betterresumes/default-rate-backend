#!/usr/bin/env python3

import secrets
import string
import re
from sqlalchemy.orm import Session
from typing import Optional
from ..core.database import Tenant, Organization, OrganizationMemberWhitelist, User

# ========================================
# TOKEN GENERATION UTILITIES
# ========================================

def generate_join_token() -> str:
    """Generate secure 32-character join token for organizations"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

def generate_slug(name: str) -> str:
    """Generate URL-friendly slug from name"""
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r'[^a-zA-Z0-9\s-]', '', name.lower())
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')
    return slug

# ========================================
# ORGANIZATION UTILITIES
# ========================================

def is_organization_name_unique(db: Session, name: str, exclude_id: Optional[str] = None) -> bool:
    """Check if organization name is unique across platform"""
    query = db.query(Organization).filter(Organization.name == name)
    if exclude_id:
        query = query.filter(Organization.id != exclude_id)
    return query.first() is None

def is_slug_unique(db: Session, slug: str, table_class, exclude_id: Optional[str] = None) -> bool:
    """Check if slug is unique for given table"""
    query = db.query(table_class).filter(table_class.slug == slug)
    if exclude_id:
        query = query.filter(table_class.id != exclude_id)
    return query.first() is None

def generate_unique_slug(db: Session, name: str, table_class, exclude_id: Optional[str] = None) -> str:
    """Generate unique slug, adding numbers if needed"""
    base_slug = generate_slug(name)
    slug = base_slug
    counter = 1
    
    while not is_slug_unique(db, slug, table_class, exclude_id):
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    return slug

# ========================================
# WHITELIST UTILITIES
# ========================================

def is_email_whitelisted(db: Session, organization_id: str, email: str) -> bool:
    """Check if email is whitelisted for organization"""
    whitelist_entry = db.query(OrganizationMemberWhitelist).filter(
        OrganizationMemberWhitelist.organization_id == organization_id,
        OrganizationMemberWhitelist.email == email.lower(),
        OrganizationMemberWhitelist.status == "active"
    ).first()
    return whitelist_entry is not None

def add_email_to_whitelist(db: Session, organization_id: str, email: str, added_by: str) -> bool:
    """Add email to organization whitelist"""
    try:
        # Check if already exists
        existing = db.query(OrganizationMemberWhitelist).filter(
            OrganizationMemberWhitelist.organization_id == organization_id,
            OrganizationMemberWhitelist.email == email.lower()
        ).first()
        
        if existing:
            # Reactivate if inactive
            if existing.status == "inactive":
                existing.status = "active"
                db.commit()
                return True
            return False  # Already active
        
        # Create new whitelist entry
        whitelist_entry = OrganizationMemberWhitelist(
            organization_id=organization_id,
            email=email.lower(),
            added_by=added_by,
            status="active"
        )
        db.add(whitelist_entry)
        db.commit()
        return True
    except Exception:
        db.rollback()
        return False

def remove_email_from_whitelist(db: Session, organization_id: str, email: str) -> bool:
    """Remove email from organization whitelist"""
    try:
        whitelist_entry = db.query(OrganizationMemberWhitelist).filter(
            OrganizationMemberWhitelist.organization_id == organization_id,
            OrganizationMemberWhitelist.email == email.lower()
        ).first()
        
        if whitelist_entry:
            db.delete(whitelist_entry)
            db.commit()
            return True
        return False
    except Exception:
        db.rollback()
        return False

# ========================================
# ROLE VALIDATION UTILITIES
# ========================================

def get_user_effective_role(user: User) -> str:
    """Get user's effective role for permission checking"""
    if user.global_role == "super_admin":
        return "super_admin"
    elif user.global_role == "tenant_admin":
        return "tenant_admin"
    elif user.organization_id and user.organization_role:
        return f"org_{user.organization_role}"  # org_admin or org_member
    else:
        return "user"  # No organization

def can_access_tenant(user: User, tenant_id: str) -> bool:
    """Check if user can access tenant data"""
    if user.global_role == "super_admin":
        return True
    if user.global_role == "tenant_admin" and str(user.tenant_id) == tenant_id:
        return True
    return False

def can_access_organization(user: User, organization_id: str) -> bool:
    """Check if user can access organization data"""
    if user.global_role == "super_admin":
        return True
    if user.organization_id and str(user.organization_id) == organization_id:
        return True
    # Tenant admin can access all orgs in their tenant
    if user.global_role == "tenant_admin" and user.tenant_id:
        # Need to check if org belongs to user's tenant
        # This would require a database query in actual implementation
        return True  # Simplified for now
    return False

def can_manage_organization(user: User, organization_id: str) -> bool:
    """Check if user can manage organization (admin functions)"""
    if user.global_role == "super_admin":
        return True
    if (user.organization_id and str(user.organization_id) == organization_id and 
        user.organization_role == "admin"):
        return True
    # Tenant admin can manage orgs in their tenant
    if user.global_role == "tenant_admin" and user.tenant_id:
        return True  # Simplified for now
    return False

# ========================================
# DATA ACCESS UTILITIES
# ========================================

def get_accessible_predictions_filter(user: User):
    """Get SQLAlchemy filter for predictions user can access"""
    if user.global_role == "super_admin":
        # Super admin sees everything
        return None  # No filter needed
    elif user.organization_id:
        # Organization members see:
        # 1. Their organization's predictions
        # 2. Super admin predictions (organization_id = NULL)
        return [
            {"organization_id": user.organization_id},
            {"organization_id": None}
        ]
    else:
        # Users without organization see only super admin predictions
        return [{"organization_id": None}]

def get_user_context(user: User) -> dict:
    """Get user context for UI/API responses"""
    return {
        "user_id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "global_role": user.global_role,
        "organization_id": str(user.organization_id) if user.organization_id else None,
        "organization_role": user.organization_role,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "effective_role": get_user_effective_role(user)
    }

# ========================================
# TENANT UTILITIES
# ========================================

def create_tenant_slug(name: str) -> str:
    """Create tenant slug from name"""
    return generate_slug(name)

def validate_tenant_domain(domain: str) -> bool:
    """Validate tenant domain format"""
    # Basic domain validation
    domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}$'
    return bool(re.match(domain_pattern, domain))

def create_organization_slug(name: str) -> str:
    """Create organization slug from name"""
    return generate_slug(name)

def validate_organization_domain(domain: str) -> bool:
    """Validate organization domain format"""
    # Basic domain validation
    domain_pattern = r'^[a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]?\.[a-zA-Z]{2,}$'
    return bool(re.match(domain_pattern, domain))

def get_organization_by_token(db: Session, join_token: str) -> Optional[Organization]:
    """Get organization by join token"""
    return db.query(Organization).filter(
        Organization.join_token == join_token,
        Organization.is_active == True
    ).first()
