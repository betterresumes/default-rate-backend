#!/usr/bin/env python3
"""
Create Super Admin User in RDS Database
Direct database insertion - no APIs needed
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# Import required modules
try:
    import psycopg2
    from passlib.context import CryptContext
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Please install: pip install psycopg2-binary passlib[bcrypt]")
    sys.exit(1)

# RDS Database configuration
DB_CONFIG = {
    'host': 'accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'accunode_admin',
    'password': 'AccuNode2024!SecurePass'
}

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=8)

def create_super_admin_user():
    """Create super admin user directly in RDS"""
    print("👑 CREATING SUPER ADMIN IN RDS DATABASE")
    print("=" * 50)
    
    # Super admin details
    user_id = str(uuid.uuid4())
    email = "admin@accunode.ai"
    username = "accunode"
    password = "SuperaAdmin123*"
    full_name = "accunode.ai"
    role = "super_admin"
    
    print(f"📋 Super Admin Details:")
    print(f"   Email: {email}")
    print(f"   Username: {username}")
    print(f"   Full Name: {full_name}")
    print(f"   Role: {role}")
    print(f"   Password: {password}")
    
    try:
        # Connect to RDS
        print(f"\n🔗 Connecting to RDS database...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("✅ Connected to RDS successfully!")
        
        # Check if users table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            print("⚠️ Users table doesn't exist. Creating table...")
            
            # Create users table (basic structure)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT true,
                    tenant_id UUID,
                    organization_id UUID,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            print("✅ Users table created!")
        
        # Check if user already exists
        cur.execute(
            "SELECT id, email, role FROM users WHERE email = %s OR username = %s",
            (email, username)
        )
        
        existing_user = cur.fetchone()
        
        if existing_user:
            print(f"⚠️ User already exists:")
            print(f"   ID: {existing_user[0]}")
            print(f"   Email: {existing_user[1]}")
            print(f"   Role: {existing_user[2]}")
            
            # Update existing user to super_admin
            cur.execute("""
                UPDATE users 
                SET role = %s, 
                    hashed_password = %s,
                    updated_at = %s,
                    is_active = true
                WHERE email = %s
            """, (role, pwd_context.hash(password), datetime.utcnow(), email))
            
            print("✅ Updated existing user to super admin!")
            
        else:
            # Hash password
            hashed_password = pwd_context.hash(password)
            
            # Insert super admin user
            cur.execute("""
                INSERT INTO users (
                    id, email, username, hashed_password, full_name, 
                    role, is_active, tenant_id, organization_id, 
                    created_at, updated_at
                ) VALUES (
                    %s, %s, %s, %s, %s, 
                    %s, %s, %s, %s, 
                    %s, %s
                )
            """, (
                user_id, email, username, hashed_password, full_name,
                role, True, None, None,
                datetime.utcnow(), datetime.utcnow()
            ))
            
            print("✅ Super admin user created successfully!")
        
        # Commit changes
        conn.commit()
        
        # Verify creation
        cur.execute("SELECT id, email, username, role, is_active FROM users WHERE email = %s", (email,))
        created_user = cur.fetchone()
        
        if created_user:
            print(f"\n🎉 SUPER ADMIN VERIFICATION:")
            print(f"   ID: {created_user[0]}")
            print(f"   Email: {created_user[1]}")
            print(f"   Username: {created_user[2]}")
            print(f"   Role: {created_user[3]}")
            print(f"   Active: {created_user[4]}")
            
            print(f"\n🔐 Login Credentials:")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def inspect_database():
    """Quick database inspection"""
    print(f"\n🔍 DATABASE INSPECTION")
    print("=" * 30)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # List all tables
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        
        tables = cur.fetchall()
        print(f"📋 Tables in database:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Count users if table exists
        if any('users' in table for table in tables):
            cur.execute("SELECT COUNT(*) FROM users;")
            user_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin';")
            admin_count = cur.fetchone()[0]
            
            print(f"\n📊 User Statistics:")
            print(f"   Total Users: {user_count}")
            print(f"   Super Admins: {admin_count}")
            
            # List super admins
            if admin_count > 0:
                cur.execute("SELECT email, username, is_active FROM users WHERE role = 'super_admin';")
                admins = cur.fetchall()
                print(f"\n👑 Super Admins:")
                for admin in admins:
                    status = "🟢" if admin[2] else "🔴"
                    print(f"   {status} {admin[0]} ({admin[1]})")
        
    except Exception as e:
        print(f"❌ Error inspecting database: {e}")
        
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

def main():
    """Main function"""
    print("🚀 RDS SUPER ADMIN SETUP")
    print("=" * 30)
    
    # Test connection first
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        print(f"✅ RDS Connection successful!")
        print(f"📊 PostgreSQL: {version.split(',')[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ RDS Connection failed: {e}")
        return
    
    # Inspect current state
    inspect_database()
    
    # Create super admin
    print(f"\n" + "="*50)
    success = create_super_admin_user()
    
    if success:
        print(f"\n" + "="*50)
        print("🎉 SETUP COMPLETE!")
        print("You can now use the super admin credentials to access admin APIs")
        print("="*50)
    else:
        print(f"\n❌ Setup failed!")

if __name__ == "__main__":
    main()
