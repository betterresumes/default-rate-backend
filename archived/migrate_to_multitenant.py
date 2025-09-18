#!/usr/bin/env python3
"""
Database migration script to update existing database with multi-tenant schema
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return database_url

def run_migration():
    """Run database migration to add multi-tenant support"""
    print("🔄 Starting database migration for multi-tenant support...")
    
    engine = create_engine(get_database_url())
    
    with engine.connect() as conn:
        # Begin transaction
        trans = conn.begin()
        
        try:
            inspector = inspect(engine)
            
            # Check existing tables and columns
            existing_tables = inspector.get_table_names()
            print(f"📋 Found existing tables: {existing_tables}")
            
            # 1. Create tenants table if it doesn't exist
            if 'tenants' not in existing_tables:
                print("📝 Creating tenants table...")
                conn.execute(text("""
                    CREATE TABLE tenants (
                        id UUID PRIMARY KEY,
                        name VARCHAR(100) NOT NULL,
                        slug VARCHAR(100) UNIQUE NOT NULL,
                        domain VARCHAR(100) UNIQUE,
                        description TEXT,
                        logo_url VARCHAR(500),
                        max_organizations INTEGER NOT NULL DEFAULT 50,
                        is_active BOOLEAN NOT NULL DEFAULT true,
                        created_by UUID NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        updated_at TIMESTAMP
                    )
                """))
                print("✅ Tenants table created")
            
            # 2. Create organization_member_whitelist table if it doesn't exist
            if 'organization_member_whitelist' not in existing_tables:
                print("📝 Creating organization_member_whitelist table...")
                conn.execute(text("""
                    CREATE TABLE organization_member_whitelist (
                        id UUID PRIMARY KEY,
                        organization_id UUID NOT NULL,
                        email VARCHAR(255) NOT NULL,
                        added_by UUID NOT NULL,
                        added_at TIMESTAMP NOT NULL DEFAULT NOW(),
                        status VARCHAR(20) NOT NULL DEFAULT 'active',
                        CONSTRAINT fk_whitelist_organization FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                        CONSTRAINT fk_whitelist_added_by FOREIGN KEY (added_by) REFERENCES users(id),
                        UNIQUE(organization_id, email)
                    )
                """))
                print("✅ Organization member whitelist table created")
            
            # 3. Check and modify organizations table
            if 'organizations' in existing_tables:
                org_columns = [col['name'] for col in inspector.get_columns('organizations')]
                print(f"📋 Organizations table columns: {org_columns}")
                
                # Add missing columns to organizations table
                missing_org_columns = {
                    'tenant_id': 'UUID',
                    'slug': 'VARCHAR(100) UNIQUE',
                    'domain': 'VARCHAR(100) UNIQUE',
                    'logo_url': 'VARCHAR(500)',
                    'max_users': 'INTEGER NOT NULL DEFAULT 100',
                    'join_token': 'VARCHAR(100) UNIQUE',
                    'join_enabled': 'BOOLEAN NOT NULL DEFAULT true',
                    'default_role': 'VARCHAR(20) NOT NULL DEFAULT \'user\'',
                    'join_created_at': 'TIMESTAMP',
                    'updated_at': 'TIMESTAMP'
                }
                
                for col_name, col_type in missing_org_columns.items():
                    if col_name not in org_columns:
                        print(f"📝 Adding {col_name} to organizations table...")
                        conn.execute(text(f"ALTER TABLE organizations ADD COLUMN {col_name} {col_type}"))
                        print(f"✅ Added {col_name} column")
                
                # Add foreign key constraint for tenant_id if it doesn't exist
                try:
                    conn.execute(text("""
                        ALTER TABLE organizations 
                        ADD CONSTRAINT fk_organizations_tenant 
                        FOREIGN KEY (tenant_id) REFERENCES tenants(id) ON DELETE SET NULL
                    """))
                    print("✅ Added tenant foreign key constraint")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        print("⚠️ Tenant foreign key constraint already exists")
                    else:
                        print(f"⚠️ Could not add tenant foreign key: {e}")
            
            # 4. Check and modify users table
            if 'users' in existing_tables:
                user_columns = [col['name'] for col in inspector.get_columns('users')]
                print(f"📋 Users table columns: {user_columns}")
                
                # Add missing columns to users table
                missing_user_columns = {
                    'tenant_id': 'UUID',
                    'organization_role': 'VARCHAR(20) NOT NULL DEFAULT \'user\'',
                    'global_role': 'VARCHAR(20) NOT NULL DEFAULT \'user\'',
                    'is_verified': 'BOOLEAN NOT NULL DEFAULT true',
                    'joined_via_token': 'VARCHAR(100)',
                    'whitelist_email': 'VARCHAR(255)',
                    'updated_at': 'TIMESTAMP',
                    'last_login': 'TIMESTAMP'
                }
                
                for col_name, col_type in missing_user_columns.items():
                    if col_name not in user_columns:
                        print(f"📝 Adding {col_name} to users table...")
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                        print(f"✅ Added {col_name} column")
            
            # 5. Update prediction tables to add organization_id
            for table_name in ['annual_predictions', 'quarterly_predictions']:
                if table_name in existing_tables:
                    pred_columns = [col['name'] for col in inspector.get_columns(table_name)]
                    if 'organization_id' not in pred_columns:
                        print(f"📝 Adding organization_id to {table_name} table...")
                        conn.execute(text(f"""
                            ALTER TABLE {table_name} 
                            ADD COLUMN organization_id UUID,
                            ADD CONSTRAINT fk_{table_name}_organization 
                            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE SET NULL
                        """))
                        print(f"✅ Added organization_id to {table_name}")
            
            # 6. Create indexes for performance
            print("📝 Creating performance indexes...")
            
            # Organizations indexes
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_organizations_tenant ON organizations(tenant_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_organizations_domain ON organizations(domain)"))
            except Exception as e:
                print(f"⚠️ Could not create organization indexes: {e}")
            
            # Users indexes
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_tenant ON users(tenant_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_organization ON users(organization_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_global_role ON users(global_role)"))
            except Exception as e:
                print(f"⚠️ Could not create user indexes: {e}")
            
            # Whitelist indexes
            try:
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_whitelist_organization ON organization_member_whitelist(organization_id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS idx_whitelist_email ON organization_member_whitelist(email)"))
            except Exception as e:
                print(f"⚠️ Could not create whitelist indexes: {e}")
            
            # Commit transaction
            trans.commit()
            print("✅ Database migration completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Migration failed: {e}")
            raise
    
    print("🎉 Multi-tenant database schema is ready!")

if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        print(f"💥 Migration error: {e}")
        sys.exit(1)
