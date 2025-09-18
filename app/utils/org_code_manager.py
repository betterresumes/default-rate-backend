"""
Organization Code Management Utilities
Handles organization code generation, validation, and management
"""

import secrets
import string
from sqlalchemy.orm import Session
from ..core.database import Organization

class OrganizationCodeManager:
    """Manages organization codes for team joining"""
    
    # Characters to use in codes (avoiding confusing ones)
    VALID_CHARS = string.ascii_uppercase + string.digits
    EXCLUDED_CHARS = ['0', 'O', 'I', '1', 'L']  # Avoid confusion
    
    @classmethod
    def _get_code_chars(cls):
        """Get valid characters for code generation"""
        return ''.join(c for c in cls.VALID_CHARS if c not in cls.EXCLUDED_CHARS)
    
    @classmethod
    def generate_code(cls, db: Session, length: int = 8) -> str:
        """
        Generate a unique organization code
        
        Args:
            db: Database session
            length: Code length (default 8)
            
        Returns:
            Unique organization code
        """
        max_attempts = 100
        code_chars = cls._get_code_chars()
        
        for _ in range(max_attempts):
            code = ''.join(secrets.choice(code_chars) for _ in range(length))
            
            # Check if code already exists
            existing = db.query(Organization).filter(
                Organization.organization_code == code
            ).first()
            
            if not existing:
                return code
        
        raise Exception("Failed to generate unique organization code after multiple attempts")
    
    @classmethod
    def validate_code(cls, db: Session, code: str) -> Organization:
        """
        Validate organization code and return organization
        
        Args:
            db: Database session
            code: Organization code to validate
            
        Returns:
            Organization if valid, None if invalid
        """
        if not code or len(code) != 8:
            return None
            
        org = db.query(Organization).filter(
            Organization.organization_code == code.upper(),
            Organization.code_enabled == True,
            Organization.is_active == True
        ).first()
        
        return org
    
    @classmethod
    def regenerate_code(cls, db: Session, organization_id: str) -> str:
        """
        Regenerate code for an organization
        
        Args:
            db: Database session
            organization_id: Organization UUID
            
        Returns:
            New organization code
        """
        org = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not org:
            raise ValueError("Organization not found")
        
        new_code = cls.generate_code(db)
        org.organization_code = new_code
        db.commit()
        
        return new_code
    
    @classmethod
    def disable_code(cls, db: Session, organization_id: str) -> bool:
        """
        Disable organization code (prevent new joins)
        
        Args:
            db: Database session
            organization_id: Organization UUID
            
        Returns:
            True if successful
        """
        org = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not org:
            return False
        
        org.code_enabled = False
        db.commit()
        return True
    
    @classmethod
    def enable_code(cls, db: Session, organization_id: str) -> bool:
        """
        Enable organization code (allow new joins)
        
        Args:
            db: Database session
            organization_id: Organization UUID
            
        Returns:
            True if successful
        """
        org = db.query(Organization).filter(
            Organization.id == organization_id
        ).first()
        
        if not org:
            return False
        
        org.code_enabled = True
        db.commit()
        return True
