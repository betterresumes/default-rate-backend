#!/usr/bin/env python3

"""
Super Admin Creation Script
Creates the first super admin user for the multi-tenant platform
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from src.database import get_db, create_tables, User
from src.tenant_utils import generate_unique_slug
from passlib.context import CryptContext
import uuid
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_super_admin(
    email: str,
    username: str, 
    password: str,
    full_name: str = None
):
    """Create the first super admin user"""
    
    # Create tables if they don't exist
    try:
        create_tables()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    # Get database session
    db = next(get_db())
    
    try:
        # Check if super admin already exists
        existing_admin = db.query(User).filter(
            User.global_role == "super_admin"
        ).first()
        
        if existing_admin:
            print(f"❌ Super admin already exists: {existing_admin.email}")
            return False
        
        # Check if email already exists
        existing_user = db.query(User).filter(User.email == email.lower()).first()
        if existing_user:
            print(f"❌ User with email {email} already exists")
            return False
        
        # Check if username already exists
        existing_username = db.query(User).filter(User.username == username.lower()).first()
        if existing_username:
            print(f"❌ Username {username} already taken")
            return False
        
        # Create super admin user
        super_admin = User(
            id=uuid.uuid4(),
            email=email.lower(),
            username=username.lower(),
            hashed_password=hash_password(password),
            full_name=full_name,
            global_role="super_admin",
            organization_role=None,
            tenant_id=None,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(super_admin)
        db.commit()
        
        print("✅ Super admin created successfully!")
        print(f"   Email: {email}")
        print(f"   Username: {username}")
        print(f"   Full Name: {full_name}")
        print(f"   ID: {super_admin.id}")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating super admin: {e}")
        return False
    finally:
        db.close()

def main():
    print("🔧 Super Admin Creation Script")
    print("=" * 50)
    
    # Get input from user
    email = input("Enter super admin email: ").strip()
    if not email:
        print("❌ Email is required")
        return
    
    username = input("Enter super admin username: ").strip()
    if not username:
        print("❌ Username is required")
        return
    
    password = input("Enter super admin password (min 8 chars): ").strip()
    if not password or len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return
    
    full_name = input("Enter full name (optional): ").strip()
    if not full_name:
        full_name = None
    
    print("\n🔍 Creating super admin with:")
    print(f"   Email: {email}")
    print(f"   Username: {username}")
    print(f"   Full Name: {full_name}")
    
    confirm = input("\nProceed? (y/N): ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    success = create_super_admin(email, username, password, full_name)
    
    if success:
        print("\n🎉 Super admin setup complete!")
        print("You can now use these credentials to log in to the platform.")
    else:
        print("\n❌ Super admin creation failed!")

if __name__ == "__main__":
    main()
