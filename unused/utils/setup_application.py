#!/usr/bin/env python3
"""
Application Setup Script - Complete Role Hierarchy
=================================================

This script sets up the complete application with:
- 1 Super Admin
- 2 Tenants with 2 Tenant Admins each  
- 2 Organizations (1 in each tenant) with 1 Org Admin each
- 2 Org Members for each organization (4 total)
- 2 Normal Users
- Sample global companies

New 5-Role System:
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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, User, Tenant, Organization, Company
from app.core.database import get_database_url

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

def create_engine_and_session():
    """Create database engine and session"""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)  # Set to False for cleaner output
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return engine, SessionLocal

def setup_complete_application(session):
    """Create complete application setup with proper role hierarchy"""
    print("🚀 Setting up complete application with new 5-role system...")
    
    # ===================================
    # 1. SUPER ADMIN (1 user)
    # ===================================
    print("\n👑 Creating Super Admin...")
    super_admin = User(
        id=str(uuid.uuid4()),
        email="superadmin@defaultrate.com",
        username="superadmin",
        hashed_password=pwd_context.hash("SuperAdmin123!"),
        full_name="System Super Administrator",
        role="super_admin",
        tenant_id=None,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(super_admin)
    session.flush()
    
    # ===================================
    # 2. TENANTS (2 tenants)
    # ===================================
    print("\n🏢 Creating 2 Tenants...")
    
    tenant1 = Tenant(
        id=str(uuid.uuid4()),
        name="TechCorp Industries",
        slug="techcorp-industries",
        domain="techcorp.com",
        description="Technology corporation tenant",
        created_by=super_admin.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(tenant1)
    session.flush()
    
    tenant2 = Tenant(
        id=str(uuid.uuid4()),
        name="FinanceGroup Ltd",
        slug="financegroup-ltd",
        domain="financegroup.com",
        description="Financial services tenant",
        created_by=super_admin.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(tenant2)
    session.flush()
    
    # ===================================
    # 3. TENANT ADMINS (2 per tenant = 4 total)
    # ===================================
    print("\n👔 Creating 4 Tenant Admins (2 per tenant)...")
    
    # Tenant 1 Admins
    tenant1_admin1 = User(
        id=str(uuid.uuid4()),
        email="admin1@techcorp.com",
        username="techcorp_admin1",
        hashed_password=pwd_context.hash("TenantAdmin123!"),
        full_name="TechCorp Primary Admin",
        role="tenant_admin",
        tenant_id=tenant1.id,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(tenant1_admin1)
    
    tenant1_admin2 = User(
        id=str(uuid.uuid4()),
        email="admin2@techcorp.com",
        username="techcorp_admin2",
        hashed_password=pwd_context.hash("TenantAdmin123!"),
        full_name="TechCorp Secondary Admin",
        role="tenant_admin",
        tenant_id=tenant1.id,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(tenant1_admin2)
    
    # Tenant 2 Admins
    tenant2_admin1 = User(
        id=str(uuid.uuid4()),
        email="admin1@financegroup.com",
        username="finance_admin1",
        hashed_password=pwd_context.hash("TenantAdmin123!"),
        full_name="FinanceGroup Primary Admin",
        role="tenant_admin",
        tenant_id=tenant2.id,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(tenant2_admin1)
    
    tenant2_admin2 = User(
        id=str(uuid.uuid4()),
        email="admin2@financegroup.com",
        username="finance_admin2",
        hashed_password=pwd_context.hash("TenantAdmin123!"),
        full_name="FinanceGroup Secondary Admin",
        role="tenant_admin",
        tenant_id=tenant2.id,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(tenant2_admin2)
    session.flush()
    
    # ===================================
    # 4. ORGANIZATIONS (1 per tenant = 2 total)
    # ===================================
    print("\n🏛️ Creating 2 Organizations (1 per tenant)...")
    
    org1 = Organization(
        id=str(uuid.uuid4()),
        tenant_id=tenant1.id,
        name="TechCorp Engineering",
        slug="techcorp-engineering",
        domain="engineering.techcorp.com",
        description="Engineering department of TechCorp",
        join_token=str(uuid.uuid4()).replace('-', '')[:16],
        join_enabled=True,
        default_role="org_member",
        created_by=tenant1_admin1.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org1)
    session.flush()
    
    org2 = Organization(
        id=str(uuid.uuid4()),
        tenant_id=tenant2.id,
        name="FinanceGroup Analytics",
        slug="financegroup-analytics",
        domain="analytics.financegroup.com",
        description="Analytics department of FinanceGroup",
        join_token=str(uuid.uuid4()).replace('-', '')[:16],
        join_enabled=True,
        default_role="org_member",
        created_by=tenant2_admin1.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org2)
    session.flush()
    
    # ===================================
    # 5. ORGANIZATION ADMINS (1 per org = 2 total)
    # ===================================
    print("\n👨‍💼 Creating 2 Organization Admins (1 per org)...")
    
    org1_admin = User(
        id=str(uuid.uuid4()),
        email="orgadmin@engineering.techcorp.com",
        username="techcorp_org_admin",
        hashed_password=pwd_context.hash("OrgAdmin123!"),
        full_name="TechCorp Engineering Admin",
        role="org_admin",
        tenant_id=None,
        organization_id=org1.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org1_admin)
    
    org2_admin = User(
        id=str(uuid.uuid4()),
        email="orgadmin@analytics.financegroup.com",
        username="finance_org_admin",
        hashed_password=pwd_context.hash("OrgAdmin123!"),
        full_name="FinanceGroup Analytics Admin",
        role="org_admin",
        tenant_id=None,
        organization_id=org2.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org2_admin)
    session.flush()
    
    # ===================================
    # 6. ORGANIZATION MEMBERS (2 per org = 4 total)
    # ===================================
    print("\n👥 Creating 4 Organization Members (2 per org)...")
    
    # Org 1 Members
    org1_member1 = User(
        id=str(uuid.uuid4()),
        email="john.doe@engineering.techcorp.com",
        username="john_doe_techcorp",
        hashed_password=pwd_context.hash("OrgMember123!"),
        full_name="John Doe",
        role="org_member",
        tenant_id=None,
        organization_id=org1.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org1_member1)
    
    org1_member2 = User(
        id=str(uuid.uuid4()),
        email="jane.smith@engineering.techcorp.com",
        username="jane_smith_techcorp",
        hashed_password=pwd_context.hash("OrgMember123!"),
        full_name="Jane Smith",
        role="org_member",
        tenant_id=None,
        organization_id=org1.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org1_member2)
    
    # Org 2 Members
    org2_member1 = User(
        id=str(uuid.uuid4()),
        email="alex.johnson@analytics.financegroup.com",
        username="alex_johnson_finance",
        hashed_password=pwd_context.hash("OrgMember123!"),
        full_name="Alex Johnson",
        role="org_member",
        tenant_id=None,
        organization_id=org2.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org2_member1)
    
    org2_member2 = User(
        id=str(uuid.uuid4()),
        email="sara.wilson@analytics.financegroup.com",
        username="sara_wilson_finance",
        hashed_password=pwd_context.hash("OrgMember123!"),
        full_name="Sara Wilson",
        role="org_member",
        tenant_id=None,
        organization_id=org2.id,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(org2_member2)
    
    # ===================================
    # 7. NORMAL USERS (2 users)
    # ===================================
    print("\n👤 Creating 2 Normal Users...")
    
    user1 = User(
        id=str(uuid.uuid4()),
        email="user1@example.com",
        username="normal_user1",
        hashed_password=pwd_context.hash("User123!"),
        full_name="Normal User One",
        role="user",
        tenant_id=None,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(user1)
    
    user2 = User(
        id=str(uuid.uuid4()),
        email="user2@example.com",
        username="normal_user2",
        hashed_password=pwd_context.hash("User123!"),
        full_name="Normal User Two",
        role="user",
        tenant_id=None,
        organization_id=None,
        is_active=True,
        created_at=datetime.utcnow()
    )
    session.add(user2)
    
    # ===================================
    # 8. GLOBAL SAMPLE COMPANIES
    # ===================================
    print("\n🏭 Creating Global Sample Companies...")
    
    companies = [
        Company(
            id=str(uuid.uuid4()),
            symbol="AAPL",
            name="Apple Inc.",
            market_cap=3000000000000,
            sector="Technology",
            organization_id=None,
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
            organization_id=None,
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
            organization_id=None,
            is_global=True,
            created_by=super_admin.id,
            created_at=datetime.utcnow()
        ),
        Company(
            id=str(uuid.uuid4()),
            symbol="TSLA",
            name="Tesla Inc.",
            market_cap=800000000000,
            sector="Automotive",
            organization_id=None,
            is_global=True,
            created_by=super_admin.id,
            created_at=datetime.utcnow()
        ),
        Company(
            id=str(uuid.uuid4()),
            symbol="AMZN",
            name="Amazon.com Inc.",
            market_cap=1500000000000,
            sector="E-commerce",
            organization_id=None,
            is_global=True,
            created_by=super_admin.id,
            created_at=datetime.utcnow()
        )
    ]
    
    for company in companies:
        session.add(company)
    
    session.commit()
    print("✅ Complete application setup created successfully!")
    
    return {
        'super_admin': super_admin,
        'tenant1': tenant1,
        'tenant2': tenant2,
        'tenant1_admin1': tenant1_admin1,
        'tenant1_admin2': tenant1_admin2,
        'tenant2_admin1': tenant2_admin1,
        'tenant2_admin2': tenant2_admin2,
        'org1': org1,
        'org2': org2,
        'org1_admin': org1_admin,
        'org2_admin': org2_admin,
        'org1_member1': org1_member1,
        'org1_member2': org1_member2,
        'org2_member1': org2_member1,
        'org2_member2': org2_member2,
        'user1': user1,
        'user2': user2,
        'companies': companies
    }

def print_complete_summary(data):
    """Print comprehensive summary of created data"""
    print("\n" + "="*80)
    print("🎯 COMPLETE APPLICATION SETUP SUMMARY - NEW 5-ROLE SYSTEM")
    print("="*80)
    
    print(f"\n👑 SUPER ADMIN (1 user):")
    print(f"   {data['super_admin'].email} | {data['super_admin'].username} | Password: SuperAdmin123!")
    
    print(f"\n🏢 TENANTS (2 tenants):")
    print(f"   1. {data['tenant1'].name} ({data['tenant1'].slug}) - {data['tenant1'].domain}")
    print(f"   2. {data['tenant2'].name} ({data['tenant2'].slug}) - {data['tenant2'].domain}")
    
    print(f"\n👔 TENANT ADMINS (4 users - 2 per tenant):")
    print(f"   Tenant 1 ({data['tenant1'].name}):")
    print(f"     • {data['tenant1_admin1'].email} | {data['tenant1_admin1'].username} | Password: TenantAdmin123!")
    print(f"     • {data['tenant1_admin2'].email} | {data['tenant1_admin2'].username} | Password: TenantAdmin123!")
    print(f"   Tenant 2 ({data['tenant2'].name}):")
    print(f"     • {data['tenant2_admin1'].email} | {data['tenant2_admin1'].username} | Password: TenantAdmin123!")
    print(f"     • {data['tenant2_admin2'].email} | {data['tenant2_admin2'].username} | Password: TenantAdmin123!")
    
    print(f"\n🏛️ ORGANIZATIONS (2 orgs - 1 per tenant):")
    print(f"   1. {data['org1'].name} ({data['org1'].slug}) - {data['org1'].domain}")
    print(f"      Join Token: {data['org1'].join_token}")
    print(f"   2. {data['org2'].name} ({data['org2'].slug}) - {data['org2'].domain}")
    print(f"      Join Token: {data['org2'].join_token}")
    
    print(f"\n👨‍💼 ORGANIZATION ADMINS (2 users - 1 per org):")
    print(f"   Org 1 ({data['org1'].name}):")
    print(f"     • {data['org1_admin'].email} | {data['org1_admin'].username} | Password: OrgAdmin123!")
    print(f"   Org 2 ({data['org2'].name}):")
    print(f"     • {data['org2_admin'].email} | {data['org2_admin'].username} | Password: OrgAdmin123!")
    
    print(f"\n👥 ORGANIZATION MEMBERS (4 users - 2 per org):")
    print(f"   Org 1 ({data['org1'].name}):")
    print(f"     • {data['org1_member1'].email} | {data['org1_member1'].username} | Password: OrgMember123!")
    print(f"     • {data['org1_member2'].email} | {data['org1_member2'].username} | Password: OrgMember123!")
    print(f"   Org 2 ({data['org2'].name}):")
    print(f"     • {data['org2_member1'].email} | {data['org2_member1'].username} | Password: OrgMember123!")
    print(f"     • {data['org2_member2'].email} | {data['org2_member2'].username} | Password: OrgMember123!")
    
    print(f"\n👤 NORMAL USERS (2 users):")
    print(f"   • {data['user1'].email} | {data['user1'].username} | Password: User123!")
    print(f"   • {data['user2'].email} | {data['user2'].username} | Password: User123!")
    
    print(f"\n🏭 GLOBAL COMPANIES ({len(data['companies'])} companies):")
    for company in data['companies']:
        print(f"   • {company.symbol}: {company.name} ({company.sector})")
    
    print(f"\n🔐 NEW 5-ROLE HIERARCHY:")
    print(f"   1. super_admin     - Can manage everything (1 user)")
    print(f"   2. tenant_admin    - Manage tenant & orgs within tenant (4 users)")
    print(f"   3. org_admin       - Manage users in specific organization (2 users)")
    print(f"   4. org_member      - Access resources in specific organization (4 users)")
    print(f"   5. user            - Limited access, no organization (2 users)")
    
    print(f"\n📊 TOTAL USERS CREATED: {1 + 4 + 2 + 4 + 2} users")
    print(f"📊 TOTAL TENANTS: 2")
    print(f"📊 TOTAL ORGANIZATIONS: 2")
    print(f"📊 TOTAL COMPANIES: {len(data['companies'])}")
    
    print("\n✅ Complete application setup finished successfully!")
    print("🚀 You can now start the API server with: python -m app.main")
    print("🔗 API Documentation: http://localhost:8000/docs")
    print("="*80)

def main():
    """Main function to setup complete application"""
    try:
        print("🚀 Starting complete application setup with new 5-role system...")
        
        # Create engine and session
        engine, SessionLocal = create_engine_and_session()
        
        # Setup complete application
        session = SessionLocal()
        try:
            data = setup_complete_application(session)
            print_complete_summary(data)
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Error during application setup: {str(e)}")
        raise

if __name__ == "__main__":
    main()
