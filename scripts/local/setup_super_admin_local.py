#!/usr/bin/env python3
"""
Local Super Admin Setup Script for Development Environment

Usage:
    python scripts/local/setup_super_admin_local.py

Features:
- Create super admin for local development
- Connect to local PostgreSQL database
- Uses same logic as production script but for local env
"""

import psycopg2
from datetime import datetime
import uuid
import logging
from passlib.context import CryptContext

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Use the EXACT same password context as your FastAPI app
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

def get_password_hash(password: str) -> str:
    """Hash a password using the same method as FastAPI app."""
    return pwd_context.hash(password)

# Local database configuration
LOCAL_DB_CONFIG = {
    "host": "localhost",
    "database": "accunode_development", 
    "user": "admin",
    "password": "dev_password_123",
    "port": 5432
}

def create_super_admin():
    """Create super admin user using same logic as production script"""
    
    # Local admin details (different from production)
    admin_email = "local@accunode.ai"
    admin_password = "LocalAdmin2024!"
    admin_name = "Local Super Administrator"
    admin_username = "super_admin"
    
    print("🎯 Creating Local Super Admin User (Bcrypt Hashing)")
    print("=" * 50)
    print(f"📧 Email: {admin_email}")
    print(f"👤 Name: {admin_name}")
    print(f"🔑 Username: {admin_username}")
    print("🌟 Super Admin (No tenant/org restrictions)")
    print("🏠 Environment: LOCAL DEVELOPMENT")
    
    try:
        # Connect to local database
        print("\n🔌 Connecting to local database...")
        conn = psycopg2.connect(**LOCAL_DB_CONFIG)
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
        existing_user = cur.fetchone()
        
        if existing_user:
            print(f"\n❌ User with email {admin_email} already exists!")
            # Show existing user details
            cur.execute("SELECT id, email, username, role FROM users WHERE email = %s", (admin_email,))
            user_info = cur.fetchone()
            print(f"   Existing user: ID={user_info[0]}, Email={user_info[1]}, Username={user_info[2]}, Role={user_info[3]}")
            return True
        
        # Hash the password using bcrypt (same as FastAPI)
        print("🔐 Hashing password with bcrypt...")
        hashed_password = get_password_hash(admin_password)
        print(f"✅ Password hashed successfully (bcrypt)")
        
        # Generate UUID for user ID
        user_id = str(uuid.uuid4())
        
        # Insert super admin user with NULL for tenant_id and organization_id
        insert_query = """
        INSERT INTO users (
            id, email, username, hashed_password, full_name, 
            tenant_id, organization_id, role, is_active, 
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id, email
        """
        
        now = datetime.utcnow()
        cur.execute(insert_query, (
            user_id,
            admin_email,
            admin_username,
            hashed_password,
            admin_name,
            None,  # tenant_id = NULL
            None,  # organization_id = NULL
            'super_admin',
            True,
            now,
            now
        ))
        
        created_user_id, email = cur.fetchone()
        conn.commit()
        
        print(f"\n🎉 Super admin created successfully!")
        print(f"   User ID: {created_user_id}")
        print(f"   Email: {email}")
        print(f"   Username: {admin_username}")
        print(f"   Name: {admin_name}")
        print(f"   Password: {admin_password}")
        print(f"   Role: super_admin")
        print(f"   Hashing: bcrypt (matches FastAPI)")
        
        # Verify the user was created and test password
        cur.execute("""
            SELECT id, email, username, full_name, role, is_active, hashed_password
            FROM users WHERE id = %s
        """, (created_user_id,))
        user_data = cur.fetchone()
        
        if user_data:
            print(f"\n✅ Verification successful!")
            print(f"   Login credentials: {user_data[1]} / {admin_password}")
            
            # Test password verification
            stored_hash = user_data[6]
            password_valid = pwd_context.verify(admin_password, stored_hash)
            print(f"   Password verification: {'✅ VALID' if password_valid else '❌ INVALID'}")
            
            if password_valid:
                print(f"\n🚀 Ready to login at http://localhost:8000!")
            else:
                print(f"\n⚠️ Password verification failed - there may be an issue")
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if conn:
            cur.close()
            conn.close()
            print("\n🔌 Database connection closed")

def display_summary():
    """Display setup summary"""
    logger.info("\n" + "=" * 60)
    logger.info("🎯 LOCAL SUPER ADMIN SETUP COMPLETE!")
    logger.info("=" * 60)
    logger.info(" Ready for development!")
    logger.info("🌐 Access your local API at: http://localhost:8000")
    logger.info("📚 API Docs: http://localhost:8000/docs")
    logger.info("🔐 Login with: local@accunode.ai / LocalAdmin2024!")
    logger.info("=" * 60)

def main():
    """Main function"""
    logger.info("🚀 Starting Local Super Admin Setup...")
    logger.info("📍 Target: Local PostgreSQL Development Database")
    logger.info("🏠 Environment: LOCAL DEVELOPMENT ONLY")
    
    try:
        # Create super admin
        success = create_super_admin()
        
        if success:
            # Display summary
            display_summary()
            logger.info("✅ Local super admin setup completed successfully!")
        else:
            logger.error("❌ Super admin setup failed!")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        return False

if __name__ == "__main__":
    main()
