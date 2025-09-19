#!/usr/bin/env python3
"""
Database Reset Script with New 5-Role System
===========================================

This script resets the database and sets up the new role structure:
- super_admin: Can manage everything
- tenant_admin: Attached to 1 tenant, can manage multiple orgs within that tenant
- org_admin: Attached to 1 organization, can manage users in that org
- org_member: Attached to 1 organization, can access org resources
- user: No organization attachment, limited access
"""

import os
import sys
import uuid
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manually load .env file if dotenv is not available
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    os.environ[key] = value

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, User, Tenant, Organization, Company
from app.core.database import get_database_url

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

def create_engine_and_session():
    """Create database engine and session"""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal

def reset_database(engine):
    """Drop all tables and recreate them"""
    print("🗑️  Dropping all existing tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("🏗️  Creating fresh tables with new schema...")
    Base.metadata.create_all(bind=engine)
    
    print("✅ Database schema reset complete!")

def create_sample_data(session):
    """Create sample data with new role structure"""
    print("👤 Creating sample users with new role system...")
    
    # 1. Super Admin User
    super_admin = User(
        id=str(uuid.uuid4()),
        email="admin@defaultrate.com", 
        username="superadmin",
        hashed_password=generate_password_hash("Admin123!"),
        full_name="Super Administrator",
        role="super_admin",  # New role system
        tenant_id=None,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(super_admin)
    session.flush()  # Get the ID
    
    # 2. Create a Sample Tenant
    sample_tenant = Tenant(
        id=str(uuid.uuid4()),
        name="Enterprise Corp",
        slug="enterprise-corp",
        domain="enterprise.com",
        description="Sample enterprise tenant",
        created_by=super_admin.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(sample_tenant)
    session.flush()
    
    # 3. Tenant Admin User
    tenant_admin = User(
        id=str(uuid.uuid4()),
        email="tenant@enterprise.com",
        username="tenantadmin", 
        hashed_password=generate_password_hash("Tenant123!"),
        full_name="Tenant Administrator",
        role="tenant_admin",  # New role system
        tenant_id=sample_tenant.id,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(tenant_admin)
    session.flush()
    
    # 4. Create Sample Organizations under the Tenant
    org1 = Organization(
        id=str(uuid.uuid4()),
        tenant_id=sample_tenant.id,
        name="Finance Department",
        slug="finance-dept",
        domain="finance.enterprise.com",
        description="Finance department organization",
        join_token=str(uuid.uuid4()).replace('-', '')[:16],
        join_enabled=True,
        default_role="org_member",  # Updated to new role
        created_by=tenant_admin.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org1)
    session.flush()
    
    org2 = Organization(
        id=str(uuid.uuid4()),
        tenant_id=sample_tenant.id,
        name="Marketing Team", 
        slug="marketing-team",
        domain="marketing.enterprise.com",
        description="Marketing team organization",
        join_token=str(uuid.uuid4()).replace('-', '')[:16],
        join_enabled=True,
        default_role="org_member",  # Updated to new role
        created_by=tenant_admin.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org2)
    session.flush()
    
    # 5. Organization Admin User
    org_admin = User(
        id=str(uuid.uuid4()),
        email="orgadmin@finance.enterprise.com",
        username="orgadmin",
        hashed_password=generate_password_hash("OrgAdmin123!"), 
        full_name="Organization Admin",
        role="org_admin",  # New role system
        tenant_id=None,
        organization_id=org1.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org_admin)
    session.flush()
    
    # 6. Organization Members
    org_member1 = User(
        id=str(uuid.uuid4()),
        email="member1@finance.enterprise.com",
        username="member1",
        hashed_password=generate_password_hash("Member123!"),
        full_name="John Member",
        role="org_member",  # New role system
        tenant_id=None,
        organization_id=org1.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org_member1)
    
    org_member2 = User(
        id=str(uuid.uuid4()),
        email="member2@marketing.enterprise.com", 
        username="member2",
        hashed_password=generate_password_hash("Member123!"),
        full_name="Jane Member",
        role="org_member",  # New role system
        tenant_id=None,
        organization_id=org2.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org_member2)
    
    # 7. Regular User (no organization)
    regular_user = User(
        id=str(uuid.uuid4()),
        email="user@example.com",
        username="regularuser", 
        hashed_password=generate_password_hash("User123!"),
        full_name="Regular User",
        role="user",  # New role system
        tenant_id=None,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(regular_user)
    
    # 8. Create Global Sample Companies
    companies = [
        Company(
            id=str(uuid.uuid4()),
            symbol="AAPL",
            name="Apple Inc.",
            market_cap=3000000000000,
            sector="Technology",
            organization_id=None,  # Global company
            is_global=True,
            created_by=super_admin.id,
            created_at=datetime.utcnow()
        ),
        Company(
            id=str(uuid.uuid4()),
            symbol="MSFT", 
            name="Microsoft Corporation",
            market_cap=2800000000000,
            sector="Technology",
            organization_id=None,  # Global company
            is_global=True,
            created_by=super_admin.id,
            created_at=datetime.utcnow()
        ),
        Company(
            id=str(uuid.uuid4()),
            symbol="GOOGL",
            name="Alphabet Inc.",
            market_cap=1700000000000,
            sector="Technology", 
            organization_id=None,  # Global company
            is_global=True,
            created_by=super_admin.id,
            created_at=datetime.utcnow()
        )
    ]
    
    for company in companies:
        session.add(company)
    
    session.commit()
    print("✅ Sample data created successfully!")
    
    return {
        'super_admin': super_admin,
        'tenant_admin': tenant_admin,
        'org_admin': org_admin,
        'org_member1': org_member1,
        'org_member2': org_member2,
        'regular_user': regular_user,
        'tenant': sample_tenant,
        'org1': org1,
        'org2': org2,
        'companies': companies
    }

def print_summary(data):
    """Print summary of created data"""
    print("\n" + "="*60)
    print("📊 DATABASE RESET SUMMARY - NEW 5-ROLE SYSTEM")
    print("="*60)
    
    print(f"\n👤 USERS CREATED:")
    print(f"   Super Admin: {data['super_admin'].email} (password: Admin123!)")
    print(f"   Tenant Admin: {data['tenant_admin'].email} (password: Tenant123!)")
    print(f"   Org Admin: {data['org_admin'].email} (password: OrgAdmin123!)")
    print(f"   Org Member 1: {data['org_member1'].email} (password: Member123!)")
    print(f"   Org Member 2: {data['org_member2'].email} (password: Member123!)")
    print(f"   Regular User: {data['regular_user'].email} (password: User123!)")
    
    print(f"\n🏢 TENANT CREATED:")
    print(f"   {data['tenant'].name} (slug: {data['tenant'].slug})")
    
    print(f"\n🏛️ ORGANIZATIONS CREATED:")
    print(f"   {data['org1'].name} (slug: {data['org1'].slug})")
    print(f"   {data['org2'].name} (slug: {data['org2'].slug})")
    
    print(f"\n🏭 GLOBAL COMPANIES CREATED:")
    for company in data['companies']:
        print(f"   {company.symbol}: {company.name}")
    
    print(f"\n🔐 NEW ROLE HIERARCHY:")
    print(f"   1. super_admin - Can manage everything")
    print(f"   2. tenant_admin - Attached to 1 tenant, can manage multiple orgs within that tenant")
    print(f"   3. org_admin - Attached to 1 organization, can manage users in that org")
    print(f"   4. org_member - Attached to 1 organization, can access org resources")
    print(f"   5. user - No organization attachment, limited access")
    
    print("\n✅ Database reset completed successfully!")
    print("🚀 You can now start the API server with: python -m app.main")
    print("="*60)

def main():
    """Main function to reset database"""
    try:
        print("🔄 Starting database reset with new 5-role system...")
        
        # Create engine and session
        engine, SessionLocal = create_engine_and_session()
        
        # Reset database
        reset_database(engine)
        
        # Create sample data
        session = SessionLocal()
        try:
            data = create_sample_data(session)
            print_summary(data)
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error during database reset: {str(e)}")
        raise

if __name__ == "__main__":
    main()
