#!/usr/bin/env python3
"""
Script to create initial users: one regular user and one superuser
"""

import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import directly using absolute imports
from database import get_session_local, User
from passlib.context import CryptContext
import uuid
from datetime import datetime

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_users():
    """Create a regular user and a superuser"""
    print("👥 Creating initial users...")
    
    try:
        # Get database session
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        # Check if users already exist
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"⚠️  Found {existing_users} existing users. Skipping user creation.")
            return
        
        # Create regular user
        print("📝 Creating regular user...")
        regular_user = User(
            id=uuid.uuid4(),
            email="user@example.com",
            username="testuser",
            hashed_password=pwd_context.hash("Password123!"),
            full_name="Test User",
            is_active=True,
            is_verified=True,
            is_superuser=False,
            role="user",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Create superuser
        print("👑 Creating superuser...")
        superuser = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            username="admin",
            hashed_password=pwd_context.hash("AdminPassword123!"),
            full_name="Admin User",
            is_active=True,
            is_verified=True,
            is_superuser=True,
            role="admin",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Add users to database
        db.add(regular_user)
        db.add(superuser)
        db.commit()
        
        print("✅ Users created successfully!")
        print("\n📋 User Details:")
        print("Regular User:")
        print(f"  📧 Email: {regular_user.email}")
        print(f"  👤 Username: {regular_user.username}")
        print(f"  🔑 Password: Password123!")
        print(f"  🆔 ID: {regular_user.id}")
        print(f"  ✅ Verified: {regular_user.is_verified}")
        
        print("\nSuperuser:")
        print(f"  📧 Email: {superuser.email}")
        print(f"  👤 Username: {superuser.username}")
        print(f"  🔑 Password: AdminPassword123!")
        print(f"  🆔 ID: {superuser.id}")
        print(f"  👑 Admin: {superuser.is_superuser}")
        print(f"  ✅ Verified: {superuser.is_verified}")
        
        print("\n🔗 You can now login with either user to get JWT tokens for testing.")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        return False

if __name__ == "__main__":
    create_users()
