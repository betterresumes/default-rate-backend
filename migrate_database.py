#!/usr/bin/env python3
"""
Database Migration Script - Add Missing tenant_id Column
Fixes: sqlalchemy.exc.ProgrammingError: column users.tenant_id does not exist
"""

import os
import sys
from sqlalchemy import create_engine, text, Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment variables"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL not found in environment variables")
        print("Please check your .env file")
        sys.exit(1)
    return db_url

def add_missing_columns():
    """Add missing tenant_id column to users table"""
    
    try:
        # Connect to database
        engine = create_engine(get_database_url())
        connection = engine.connect()
        
        print("🔍 Checking database schema...")
        
        # Check if tenant_id column exists
        result = connection.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users' AND column_name = 'tenant_id'
        """))
        
        if result.fetchone():
            print("✅ tenant_id column already exists")
        else:
            print("🔧 Adding tenant_id column to users table...")
            
            # Add tenant_id column
            connection.execute(text("""
                ALTER TABLE users 
                ADD COLUMN tenant_id UUID REFERENCES tenants(id)
            """))
            
            # Add index for performance
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_users_tenant_id ON users(tenant_id)
            """))
            
            print("✅ tenant_id column added successfully")
        
        # Check if tenants table exists
        result = connection.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'tenants'
        """))
        
        if not result.fetchone():
            print("🔧 Creating tenants table...")
            connection.execute(text("""
                CREATE TABLE tenants (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(255) UNIQUE NOT NULL,
                    slug VARCHAR(100) UNIQUE NOT NULL,
                    domain VARCHAR(255),
                    description TEXT,
                    logo_url VARCHAR(500),
                    is_active BOOLEAN DEFAULT true,
                    created_by UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            
            # Add indexes
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_tenants_name ON tenants(name);
                CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants(slug);
            """))
            
            print("✅ tenants table created successfully")
        else:
            print("✅ tenants table already exists")
            
        # Check if organization_member_whitelist table exists
        result = connection.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'organization_member_whitelist'
        """))
        
        if not result.fetchone():
            print("🔧 Creating organization_member_whitelist table...")
            connection.execute(text("""
                CREATE TABLE organization_member_whitelist (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    organization_id UUID NOT NULL REFERENCES organizations(id),
                    email VARCHAR(255) NOT NULL,
                    added_by UUID NOT NULL REFERENCES users(id),
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20) DEFAULT 'active'
                )
            """))
            
            # Add indexes and constraints
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_org_whitelist_org_id ON organization_member_whitelist(organization_id);
                CREATE INDEX IF NOT EXISTS idx_org_whitelist_email ON organization_member_whitelist(email);
                CREATE UNIQUE INDEX IF NOT EXISTS idx_org_whitelist_unique ON organization_member_whitelist(organization_id, email);
            """))
            
            print("✅ organization_member_whitelist table created successfully")
        else:
            print("✅ organization_member_whitelist table already exists")
        
        # Commit changes
        connection.commit()
        connection.close()
        
        print("🎉 Database migration completed successfully!")
        print("\n📋 Summary of changes:")
        print("  ✅ Added tenant_id column to users table")
        print("  ✅ Created tenants table (if missing)")
        print("  ✅ Created organization_member_whitelist table (if missing)")
        print("  ✅ Added necessary indexes for performance")
        
        print("\n🚀 You can now restart your application!")
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("\n🔍 Common solutions:")
        print("  1. Check your DATABASE_URL in .env file")
        print("  2. Ensure PostgreSQL is running")
        print("  3. Verify database connection permissions")
        sys.exit(1)

if __name__ == "__main__":
    print("🗄️  Database Migration Script")
    print("=" * 50)
    add_missing_columns()
