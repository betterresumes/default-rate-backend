#!/usr/bin/env python3
"""
Setup Data Script with New 5-Role System
========================================

This script creates sample data with the exact structure requested:
- 1 super admin
- 2 tenants with 2 tenant admins (1 per tenant)
- 2 organizations (1 in each tenant) with 1 org admin each
- 2 org members per organization (4 total)
- 2 normal users
"""

import os
import sys
import uuid
from datetime import datetime
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

from app.core.database import User, Tenant, Organization, Company, get_database_url
from sqlalchemy import create_engine

# Initialize password context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

def create_session():
    """Create database session"""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=False)  # Set to False for cleaner output
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def setup_complete_role_hierarchy():
    """Setup the complete role hierarchy as requested"""
    session = create_session()
    
    try:
        print("🚀 Setting up complete role hierarchy...")
        print("=" * 60)
        
        # ============================
        # 1. SUPER ADMIN (1 user)
        # ============================
        print("👑 Creating Super Admin...")
        super_admin = User(
            id=str(uuid.uuid4()),
            email="pranitsuperadmin@gmail.com",
            username="pranitsuperadmin",
            hashed_password=pwd_context.hash("SuperAdmin123!"),
            full_name="Pranit Super Administrator",
            role="super_admin",
            tenant_id=None,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(super_admin)
        session.flush()
        
        # ============================
        # 2. TENANTS (2 tenants)
        # ============================
        print("🏢 Creating 2 Bank Tenants...")
        
        # Tenant 1: HDFC Bank
        tenant1 = Tenant(
            id=str(uuid.uuid4()),
            name="HDFC Bank Limited",
            slug="hdfc-bank-limited",
            domain="hdfcbank.com",
            description="Housing Development Finance Corporation Bank - India's premier private sector bank",
            created_by=super_admin.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant1)
        session.flush()
        
        # Tenant 2: ICICI Bank
        tenant2 = Tenant(
            id=str(uuid.uuid4()),
            name="ICICI Bank Limited",
            slug="icici-bank-limited",
            domain="icicibank.com",
            description="Industrial Credit and Investment Corporation of India Bank - Leading private sector bank",
            created_by=super_admin.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant2)
        session.flush()
        
        # ============================
        # 3. TENANT ADMINS (2 users - 1 per tenant)
        # ============================
        print("👨‍💼 Creating 2 Bank Tenant Admins...")
        
        # Tenant Admin 1 for HDFC Bank
        tenant_admin1 = User(
            id=str(uuid.uuid4()),
            email="admin@hdfcbank.com",
            username="hdfc_admin",
            hashed_password=pwd_context.hash("HdfcAdmin123!"),
            full_name="HDFC Bank Administrator",
            role="tenant_admin",
            tenant_id=tenant1.id,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant_admin1)
        session.flush()
        
        # Tenant Admin 2 for ICICI Bank
        tenant_admin2 = User(
            id=str(uuid.uuid4()),
            email="admin@icicibank.com",
            username="icici_admin",
            hashed_password=pwd_context.hash("IciciAdmin123!"),
            full_name="ICICI Bank Administrator",
            role="tenant_admin",
            tenant_id=tenant2.id,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant_admin2)
        session.flush()
        
        # ============================
        # 4. ORGANIZATIONS (4 orgs - 2 in each bank tenant)
        # ============================
        print("🏛️ Creating 4 Bank Branch Organizations...")
        
        # Organization 1: HDFC Bank Mumbai Branch
        org1 = Organization(
            id=str(uuid.uuid4()),
            tenant_id=tenant1.id,
            name="HDFC Bank Mumbai Central",
            slug="hdfc-bank-mumbai-central",
            domain="mumbaicentral.hdfcbank.com",
            description="HDFC Bank Mumbai Central Branch - Corporate Banking Division",
            join_token=str(uuid.uuid4()).replace('-', '')[:16],
            join_enabled=True,
            default_role="org_member",
            created_by=tenant_admin1.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org1)
        session.flush()
        
        # Organization 2: HDFC Bank Mumbai BKC Branch
        org2 = Organization(
            id=str(uuid.uuid4()),
            tenant_id=tenant1.id,
            name="HDFC Bank Mumbai BKC",
            slug="hdfc-bank-mumbai-bkc",
            domain="mumbaibkc.hdfcbank.com",
            description="HDFC Bank Mumbai Bandra-Kurla Complex Branch - Investment Banking Division",
            join_token=str(uuid.uuid4()).replace('-', '')[:16],
            join_enabled=True,
            default_role="org_member",
            created_by=tenant_admin1.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org2)
        session.flush()
        
        # Organization 3: ICICI Bank Mumbai Nariman Point
        org3 = Organization(
            id=str(uuid.uuid4()),
            tenant_id=tenant2.id,
            name="ICICI Bank Mumbai Nariman Point",
            slug="icici-bank-mumbai-nariman-point",
            domain="mumbainarimanpoint.icicibank.com",
            description="ICICI Bank Mumbai Nariman Point Branch - Corporate Banking & Treasury",
            join_token=str(uuid.uuid4()).replace('-', '')[:16],
            join_enabled=True,
            default_role="org_member",
            created_by=tenant_admin2.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org3)
        session.flush()
        
        # Organization 4: ICICI Bank Mumbai Andheri
        org4 = Organization(
            id=str(uuid.uuid4()),
            tenant_id=tenant2.id,
            name="ICICI Bank Mumbai Andheri",
            slug="icici-bank-mumbai-andheri",
            domain="mumbaiandheri.icicibank.com",
            description="ICICI Bank Mumbai Andheri Branch - Retail Banking & Wealth Management",
            join_token=str(uuid.uuid4()).replace('-', '')[:16],
            join_enabled=True,
            default_role="org_member",
            created_by=tenant_admin2.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org4)
        session.flush()
        
        # ============================
        # 5. ORG ADMINS (4 users - 1 per organization)
        # ============================
        print("👨‍💻 Creating 4 Branch Managers (Organization Admins)...")
        
        # Org Admin 1 for HDFC Mumbai Central
        org_admin1 = User(
            id=str(uuid.uuid4()),
            email="manager.central@hdfcbank.com",
            username="hdfc_central_manager",
            hashed_password=pwd_context.hash("HdfcManager123!"),
            full_name="Rajesh Kumar - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=org1.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org_admin1)
        session.flush()
        
        # Org Admin 2 for HDFC Mumbai BKC
        org_admin2 = User(
            id=str(uuid.uuid4()),
            email="manager.bkc@hdfcbank.com",
            username="hdfc_bkc_manager",
            hashed_password=pwd_context.hash("HdfcBkcManager123!"),
            full_name="Priya Sharma - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=org2.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org_admin2)
        session.flush()
        
        # Org Admin 3 for ICICI Nariman Point
        org_admin3 = User(
            id=str(uuid.uuid4()),
            email="manager.narimanpoint@icicibank.com",
            username="icici_nariman_manager",
            hashed_password=pwd_context.hash("IciciManager123!"),
            full_name="Amit Patel - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=org3.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org_admin3)
        session.flush()
        
        # Org Admin 4 for ICICI Andheri
        org_admin4 = User(
            id=str(uuid.uuid4()),
            email="manager.andheri@icicibank.com",
            username="icici_andheri_manager",
            hashed_password=pwd_context.hash("IciciAndheriManager123!"),
            full_name="Sneha Gupta - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=org4.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org_admin4)
        session.flush()
        
        # ============================
        # 6. ORG MEMBERS (8 users - 2 per organization)
        # ============================
        print("👥 Creating 8 Bank Employees (Organization Members)...")
        
        # Org Members for HDFC Mumbai Central
        hdfc_central_member1 = User(
            id=str(uuid.uuid4()),
            email="rohan.analyst@hdfcbank.com",
            username="rohan_hdfc_analyst",
            hashed_password=pwd_context.hash("RohanHdfc123!"),
            full_name="Rohan Singh - Risk Analyst",
            role="org_member",
            tenant_id=None,
            organization_id=org1.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(hdfc_central_member1)
        
        hdfc_central_member2 = User(
            id=str(uuid.uuid4()),
            email="kavya.officer@hdfcbank.com",
            username="kavya_hdfc_officer",
            hashed_password=pwd_context.hash("KavyaHdfc123!"),
            full_name="Kavya Nair - Credit Officer",
            role="org_member",
            tenant_id=None,
            organization_id=org1.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(hdfc_central_member2)
        
        # Org Members for HDFC Mumbai BKC
        hdfc_bkc_member1 = User(
            id=str(uuid.uuid4()),
            email="arjun.advisor@hdfcbank.com",
            username="arjun_hdfc_advisor",
            hashed_password=pwd_context.hash("ArjunHdfc123!"),
            full_name="Arjun Mehta - Investment Advisor",
            role="org_member",
            tenant_id=None,
            organization_id=org2.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(hdfc_bkc_member1)
        
        hdfc_bkc_member2 = User(
            id=str(uuid.uuid4()),
            email="neha.specialist@hdfcbank.com",
            username="neha_hdfc_specialist",
            hashed_password=pwd_context.hash("NehaHdfc123!"),
            full_name="Neha Joshi - Treasury Specialist",
            role="org_member",
            tenant_id=None,
            organization_id=org2.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(hdfc_bkc_member2)
        
        # Org Members for ICICI Nariman Point
        icici_nariman_member1 = User(
            id=str(uuid.uuid4()),
            email="vikram.analyst@icicibank.com",
            username="vikram_icici_analyst",
            hashed_password=pwd_context.hash("VikramIcici123!"),
            full_name="Vikram Rao - Financial Analyst",
            role="org_member",
            tenant_id=None,
            organization_id=org3.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(icici_nariman_member1)
        
        icici_nariman_member2 = User(
            id=str(uuid.uuid4()),
            email="ritu.manager@icicibank.com",
            username="ritu_icici_manager",
            hashed_password=pwd_context.hash("RituIcici123!"),
            full_name="Ritu Agarwal - Portfolio Manager",
            role="org_member",
            tenant_id=None,
            organization_id=org3.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(icici_nariman_member2)
        
        # Org Members for ICICI Andheri
        icici_andheri_member1 = User(
            id=str(uuid.uuid4()),
            email="aditya.consultant@icicibank.com",
            username="aditya_icici_consultant",
            hashed_password=pwd_context.hash("AdityaIcici123!"),
            full_name="Aditya Sharma - Wealth Consultant",
            role="org_member",
            tenant_id=None,
            organization_id=org4.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(icici_andheri_member1)
        
        icici_andheri_member2 = User(
            id=str(uuid.uuid4()),
            email="pooja.executive@icicibank.com",
            username="pooja_icici_executive",
            hashed_password=pwd_context.hash("PoojaIcici123!"),
            full_name="Pooja Reddy - Relationship Executive",
            role="org_member",
            tenant_id=None,
            organization_id=org4.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(icici_andheri_member2)
        
        # ============================
        # 7. NORMAL USERS (2 users - no org attachment)
        # ============================
        print("👤 Creating 2 Independent Users...")
        
        # Regular User 1
        user1 = User(
            id=str(uuid.uuid4()),
            email="consultant@defaultrate.com",
            username="independent_consultant",
            hashed_password=pwd_context.hash("Consultant123!"),
            full_name="Rajiv Malhotra - Independent Consultant",
            role="user",
            tenant_id=None,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(user1)
        
        # Regular User 2
        user2 = User(
            id=str(uuid.uuid4()),
            email="analyst@defaultrate.com",
            username="freelance_analyst",
            hashed_password=pwd_context.hash("Analyst123!"),
            full_name="Meera Iyer - Freelance Financial Analyst",
            role="user",
            tenant_id=None,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(user2)
        
        # ============================
        # 8. SAMPLE COMPANIES (for testing)
        # ============================
        print("🏭 Creating Sample Companies...")
        
        # Global Companies (accessible to all)
        companies = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "market_cap": 3000000000000,
                "sector": "Technology"
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft Corporation",
                "market_cap": 2800000000000,
                "sector": "Technology"
            },
            {
                "symbol": "GOOGL",
                "name": "Alphabet Inc.",
                "market_cap": 1700000000000,
                "sector": "Technology"
            },
            {
                "symbol": "AMZN",
                "name": "Amazon.com Inc.",
                "market_cap": 1500000000000,
                "sector": "Consumer Services"
            },
            {
                "symbol": "TSLA",
                "name": "Tesla Inc.",
                "market_cap": 800000000000,
                "sector": "Consumer Goods"
            }
        ]
        
        for comp_data in companies:
            company = Company(
                id=str(uuid.uuid4()),
                symbol=comp_data["symbol"],
                name=comp_data["name"],
                market_cap=comp_data["market_cap"],
                sector=comp_data["sector"],
                organization_id=None,  # Global company
                is_global=True,
                created_by=super_admin.id,
                created_at=datetime.utcnow()
            )
            session.add(company)\n        \n        # Commit all changes\n        session.commit()\n        print("✅ All data created successfully!")\n        \n        return {\n            'super_admin': super_admin,\n            'tenant1': tenant1,\n            'tenant2': tenant2,\n            'tenant_admin1': tenant_admin1,\n            'tenant_admin2': tenant_admin2,\n            'org1': org1,\n            'org2': org2,\n            'org3': org3,\n            'org4': org4,\n            'org_admin1': org_admin1,\n            'org_admin2': org_admin2,\n            'org_admin3': org_admin3,\n            'org_admin4': org_admin4,\n            'hdfc_central_member1': hdfc_central_member1,\n            'hdfc_central_member2': hdfc_central_member2,\n            'hdfc_bkc_member1': hdfc_bkc_member1,\n            'hdfc_bkc_member2': hdfc_bkc_member2,\n            'icici_nariman_member1': icici_nariman_member1,\n            'icici_nariman_member2': icici_nariman_member2,\n            'icici_andheri_member1': icici_andheri_member1,\n            'icici_andheri_member2': icici_andheri_member2,\n            'user1': user1,\n            'user2': user2\n        }\n        \n    except Exception as e:\n        session.rollback()\n        print(f"❌ Error creating data: {str(e)}")\n        raise\n    finally:\n        session.close()\n\ndef print_setup_summary(data):\n    """Print detailed summary of created data"""\n    print("\n" + "="*80)\n    print("📊 COMPLETE BANKING ROLE HIERARCHY SETUP SUMMARY")\n    print("="*80)\n    \n    print(f"\n👑 SUPER ADMIN (1):")\n    print(f"   Email: {data['super_admin'].email}")\n    print(f"   Username: {data['super_admin'].username}")\n    print(f"   Password: SuperAdmin123!")\n    print(f"   Role: {data['super_admin'].role}")\n    \n    print(f"\n🏢 BANK TENANTS (2):")\n    print(f"   1. {data['tenant1'].name} (slug: {data['tenant1'].slug})")\n    print(f"   2. {data['tenant2'].name} (slug: {data['tenant2'].slug})")\n    \n    print(f"\n👨‍💼 BANK ADMINISTRATORS (2):")\n    print(f"   1. {data['tenant_admin1'].email} (password: HdfcBankAdmin123!)")\n    print(f"      Username: {data['tenant_admin1'].username}")\n    print(f"      Role: {data['tenant_admin1'].role}")\n    print(f"      Tenant: {data['tenant1'].name}")\n    print(f"")\n    print(f"   2. {data['tenant_admin2'].email} (password: IciciBankAdmin123!)")\n    print(f"      Username: {data['tenant_admin2'].username}")\n    print(f"      Role: {data['tenant_admin2'].role}")\n    print(f"      Tenant: {data['tenant2'].name}")\n    \n    print(f"\n🏛️ BANK BRANCHES (4):")\n    print(f"   1. {data['org1'].name} (in {data['tenant1'].name})")\n    print(f"      Slug: {data['org1'].slug}")\n    print(f"      Join Token: {data['org1'].join_token}")\n    print(f"")\n    print(f"   2. {data['org2'].name} (in {data['tenant1'].name})")\n    print(f"      Slug: {data['org2'].slug}")\n    print(f"      Join Token: {data['org2'].join_token}")\n    print(f"")\n    print(f"   3. {data['org3'].name} (in {data['tenant2'].name})")\n    print(f"      Slug: {data['org3'].slug}")\n    print(f"      Join Token: {data['org3'].join_token}")\n    print(f"")\n    print(f"   4. {data['org4'].name} (in {data['tenant2'].name})")\n    print(f"      Slug: {data['org4'].slug}")\n    print(f"      Join Token: {data['org4'].join_token}")\n    \n    print(f"\n👨‍💻 BRANCH MANAGERS (4):")\n    print(f"   1. {data['org_admin1'].email} (password: HdfcCentralManager123!)")\n    print(f"      Username: {data['org_admin1'].username}")\n    print(f"      Role: {data['org_admin1'].role}")\n    print(f"      Organization: {data['org1'].name}")\n    print(f"")\n    print(f"   2. {data['org_admin2'].email} (password: HdfcBkcManager123!)")\n    print(f"      Username: {data['org_admin2'].username}")\n    print(f"      Role: {data['org_admin2'].role}")\n    print(f"      Organization: {data['org2'].name}")\n    print(f"")\n    print(f"   3. {data['org_admin3'].email} (password: IciciNarimanManager123!)")\n    print(f"      Username: {data['org_admin3'].username}")\n    print(f"      Role: {data['org_admin3'].role}")\n    print(f"      Organization: {data['org3'].name}")\n    print(f"")\n    print(f"   4. {data['org_admin4'].email} (password: IciciAndheriManager123!)")\n    print(f"      Username: {data['org_admin4'].username}")\n    print(f"      Role: {data['org_admin4'].role}")\n    print(f"      Organization: {data['org4'].name}")\n    \n    print(f"\n👥 BANK EMPLOYEES (8):")\n    print(f"   HDFC Bank Central Mumbai Branch:")\n    print(f"   1. {data['hdfc_central_member1'].email} (password: RohanHdfc123!)")\n    print(f"      Username: {data['hdfc_central_member1'].username}")\n    print(f"      Role: {data['hdfc_central_member1'].role}")\n    print(f"")\n    print(f"   2. {data['hdfc_central_member2'].email} (password: KavyaHdfc123!)")\n    print(f"      Username: {data['hdfc_central_member2'].username}")\n    print(f"      Role: {data['hdfc_central_member2'].role}")\n    print(f"")\n    print(f"   HDFC Bank Mumbai BKC Branch:")\n    print(f"   3. {data['hdfc_bkc_member1'].email} (password: ArjunHdfc123!)")\n    print(f"      Username: {data['hdfc_bkc_member1'].username}")\n    print(f"      Role: {data['hdfc_bkc_member1'].role}")\n    print(f"")\n    print(f"   4. {data['hdfc_bkc_member2'].email} (password: NehaHdfc123!)")\n    print(f"      Username: {data['hdfc_bkc_member2'].username}")\n    print(f"      Role: {data['hdfc_bkc_member2'].role}")\n    print(f"")\n    print(f"   ICICI Bank Nariman Point Branch:")\n    print(f"   5. {data['icici_nariman_member1'].email} (password: VikramIcici123!)")\n    print(f"      Username: {data['icici_nariman_member1'].username}")\n    print(f"      Role: {data['icici_nariman_member1'].role}")\n    print(f"")\n    print(f"   6. {data['icici_nariman_member2'].email} (password: RituIcici123!)")\n    print(f"      Username: {data['icici_nariman_member2'].username}")\n    print(f"      Role: {data['icici_nariman_member2'].role}")\n    print(f"")\n    print(f"   ICICI Bank Andheri Branch:")\n    print(f"   7. {data['icici_andheri_member1'].email} (password: AdityaIcici123!)")\n    print(f"      Username: {data['icici_andheri_member1'].username}")\n    print(f"      Role: {data['icici_andheri_member1'].role}")\n    print(f"")\n    print(f"   8. {data['icici_andheri_member2'].email} (password: PoojaIcici123!)")\n    print(f"      Username: {data['icici_andheri_member2'].username}")\n    print(f"      Role: {data['icici_andheri_member2'].role}")\n    \n    print(f"\n👤 INDEPENDENT USERS (2):")\n    print(f"   1. {data['user1'].email} (password: Consultant123!)")\n    print(f"      Username: {data['user1'].username}")\n    print(f"      Role: {data['user1'].role}")\n    print(f"")\n    print(f"   2. {data['user2'].email} (password: Analyst123!)")\n    print(f"      Username: {data['user2'].username}")\n    print(f"      Role: {data['user2'].role}")\n    \n    print(f"\n🏭 SAMPLE COMPANIES:")\n    print(f"   - AAPL: Apple Inc.")\n    print(f"   - MSFT: Microsoft Corporation")\n    print(f"   - GOOGL: Alphabet Inc.")\n    print(f"   - AMZN: Amazon.com Inc.")\n    print(f"   - TSLA: Tesla Inc.")\n    \n    print(f"\n🔐 BANKING 5-ROLE HIERARCHY:")\n    print(f"   1. super_admin - System administrator (pranitsuperadmin@gmail.com)")\n    print(f"   2. tenant_admin - Bank-wide administrator (manages all branches)")\n    print(f"   3. org_admin - Branch manager (manages branch employees)")\n    print(f"   4. org_member - Bank employee (branch-specific access)")\n    print(f"   5. user - Independent user (no organizational affiliation)")\n    \n    print(f"\n🏦 PROFESSIONAL BANKING SETUP:")\n    print(f"   - 2 Major Indian Banks: HDFC Bank Limited & ICICI Bank Limited")\n    print(f"   - 4 Mumbai Branches: Central Mumbai, BKC, Nariman Point, Andheri")\n    print(f"   - 16 Total Users: 1 Super Admin + 2 Bank Admins + 4 Branch Managers + 8 Bank Employees + 2 Independent Users")\n    print(f"   - Realistic professional emails and Indian names")\n    \n    print(f"\n✅ Professional Banking Setup completed successfully!")\n    print(f"🚀 You can now start the API server and test all role-based functionality")\n    print("="*80)\n\ndef main():\n    """Main function to setup data"""\n    try:\n        print("🎯 Setting up complete role hierarchy for Default Rate Prediction System...")\n        \n        # Setup all data\n        data = setup_complete_role_hierarchy()\n        \n        # Print summary\n        print_setup_summary(data)\n        \n    except Exception as e:\n        print(f"❌ Error during setup: {str(e)}")\n        raise\n\nif __name__ == "__main__":\n    main()
