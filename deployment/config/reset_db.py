#!/usr/bin/env python3
"""
Database reset script for the multi-tenant system
Resets all tables: tenants, organizations, users, companies, predictions, and whitelist
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the current directory to Python path
sys.path.append('/Users/nikhil/Downloads/pranit/work/final/default-rate/backend')

from app.core.database import create_database_engine, Base
from sqlalchemy import text

def reset_database():
    """
    Complete database reset for multi-tenant system
    Drops all tables and recreates them with current schema
    """
    print('🔄 Starting database reset for multi-tenant system...')
    print('=' * 60)
    
    # Create engine
    engine = create_database_engine()
    
    try:
        # Show current tables before reset
        print('📋 Current tables in database:')
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            if tables:
                for table in tables:
                    print(f'   - {table}')
            else:
                print('   No tables found')
        
        print('\n🗑️  Dropping all existing tables...')
        # Handle circular foreign key dependencies by dropping with CASCADE
        with engine.connect() as conn:
            # Drop tables in reverse dependency order with CASCADE
            drop_order = [
                'quarterly_predictions',
                'annual_predictions', 
                'companies',
                'organization_member_whitelist',
                'users',
                'organizations',
                'tenants'
            ]
            
            for table_name in drop_order:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
                    print(f'   🗑️  Dropped table: {table_name}')
                except Exception as e:
                    print(f'   ⚠️  Could not drop {table_name}: {str(e)}')
            
            conn.commit()
        
        print('✅ All tables dropped successfully')
        
        print('\n🏗️  Creating new tables with multi-tenant schema...')
        Base.metadata.create_all(bind=engine)
        print('✅ All tables created successfully')
        
        # Show new tables after reset
        print('\n📋 New tables created:')
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            for table in tables:
                print(f'   ✅ {table}')
        
        print('\n' + '=' * 60)
        print('🎉 DATABASE RESET COMPLETE!')
        print('\n📊 Multi-tenant schema includes:')
        print('   🏢 tenants - Tenant organizations (enterprise level)')
        print('   🏛️  organizations - Organizations within tenants')
        print('   👥 users - Multi-role user system (super_admin, tenant_admin, org_admin, user)')
        print('   🏢 companies - Companies with organization/tenant context')
        print('   📈 annual_predictions - Annual financial risk predictions')
        print('   📊 quarterly_predictions - Quarterly financial risk predictions')
        print('   📋 organization_member_whitelist - Email whitelist for organization joining')
        print('\n🔐 Role hierarchy: super_admin > tenant_admin > org_admin > user')
        print('📧 Email-based organization joining with whitelist system')
        print('\n⚠️  Remember to:')
        print('   1. Create a super admin user to manage the system')
        print('   2. Create tenants before organizations')
        print('   3. Set up organization whitelists for user joining')
        
    except Exception as e:
        print(f'\n❌ Error during database reset: {str(e)}')
        raise
    finally:
        engine.dispose()

def create_super_admin():
    """
    Helper function to create initial super admin user
    """
    print('\n🔧 Creating initial super admin user...')
    
    try:
        from app.core.database import get_session_local
        from app.core.database import User
        from passlib.context import CryptContext
        import uuid
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        # Check if super admin already exists
        existing_admin = db.query(User).filter(User.email == "admin@system.com").first()
        if existing_admin:
            print('⚠️  Super admin already exists with email: admin@system.com')
            return
        
        # Create super admin user
        super_admin = User(
            id=uuid.uuid4(),
            email="admin@system.com",
            username="system_admin",
            hashed_password=pwd_context.hash("SuperAdmin123!"),
            full_name="System Administrator",
            global_role="super_admin",
            is_active=True
        )
        
        db.add(super_admin)
        db.commit()
        
        print('✅ Super admin created successfully!')
        print('   📧 Email: admin@system.com')
        print('   🔑 Password: SuperAdmin123!')
        print('   👑 Role: super_admin')
        print('   ⚠️  Please change the password after first login!')
        
    except Exception as e:
        print(f'❌ Error creating super admin: {str(e)}')
        if 'db' in locals():
            db.rollback()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset database for multi-tenant system')
    parser.add_argument('--create-admin', action='store_true', 
                        help='Also create initial super admin user')
    
    args = parser.parse_args()
    
    # Always reset database
    reset_database()
    
    # Optionally create super admin
    if args.create_admin:
        create_super_admin()
    else:
        print('\n💡 Tip: Run with --create-admin to also create initial super admin user')
        print('   Example: python reset_db.py --create-admin')
