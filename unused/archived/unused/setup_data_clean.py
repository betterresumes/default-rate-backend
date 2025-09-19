#!/usr/bin/env python3
"""
Professional         # Super Admin
        super_admin = User(
            email="pranitsuperadmin@gmail.com",
            username="super_admin",
            hashed_password=pwd_context.hash("SuperAdmin123!"),
            full_name="Pranit Patil - System Administrator",
            role="super_admin",
            tenant_id=None,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        ) Data for Default Rate Prediction System
Creates a complete role hierarchy with HDFC Bank and ICICI Bank branches
"""

import os
import uuid
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import User, Tenant, Organization, Company, Base

# Database setup - using direct DATABASE_URL
DATABASE_URL = "postgresql://neondb_owner:npg_2ZLE4VuBytOa@ep-crimson-cell-adrxvu8a-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

def setup_complete_role_hierarchy():
    """Setup complete professional banking role hierarchy"""
    
    # Use the already configured session
    session = SessionLocal()
    
    try:
        print("🎯 Setting up Professional Banking Role Hierarchy...")
        
        # ============================
        # 1. SUPER ADMIN
        # ============================
        print("👑 Creating Super Admin...")
        
        super_admin = User(
            id=str(uuid.uuid4()),
            email="pranitsuperadmin@gmail.com",
            username="pranit_super_admin",
            hashed_password=pwd_context.hash("SuperAdmin123!"),
            full_name="Pranit Khanna - System Administrator",
            role="super_admin",
            tenant_id=None,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(super_admin)
        session.flush()
        
        # ============================
        # 2. BANK TENANTS (2)
        # ============================
        print("🏢 Creating 2 Major Indian Bank Tenants...")
        
        # HDFC Bank Limited
        tenant1 = Tenant(
            id=str(uuid.uuid4()),
            name="HDFC Bank Limited",
            slug="hdfc-bank",
            description="Leading private sector bank in India, offering comprehensive banking and financial services",
            is_active=True,
            created_by=super_admin.id,
            created_at=datetime.utcnow()
        )
        session.add(tenant1)
        session.flush()
        
        # ICICI Bank Limited
        tenant2 = Tenant(
            id=str(uuid.uuid4()),
            name="ICICI Bank Limited",
            slug="icici-bank",
            description="Premier private sector bank providing innovative banking solutions across India",
            is_active=True,
            created_by=super_admin.id,
            created_at=datetime.utcnow()
        )
        session.add(tenant2)
        session.flush()
        
        # ============================
        # 3. BANK ADMINISTRATORS (2)
        # ============================
        print("👨‍💼 Creating 2 Bank Administrators...")
        
        # HDFC Bank Administrator
        tenant_admin1 = User(
            id=str(uuid.uuid4()),
            email="admin.operations@hdfcbank.com",
            username="hdfc_bank_admin",
            hashed_password=pwd_context.hash("HdfcBankAdmin123!"),
            full_name="Suresh Kumar - HDFC Operations Head",
            role="tenant_admin",
            tenant_id=tenant1.id,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant_admin1)
        
        # ICICI Bank Administrator
        tenant_admin2 = User(
            id=str(uuid.uuid4()),
            email="admin.operations@icicibank.com",
            username="icici_bank_admin",
            hashed_password=pwd_context.hash("IciciBankAdmin123!"),
            full_name="Priya Sharma - ICICI Operations Head",
            role="tenant_admin",
            tenant_id=tenant2.id,
            organization_id=None,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(tenant_admin2)
        session.flush()
        
        # ============================
        # 4. BANK BRANCHES (4 organizations)
        # ============================
        print("🏛️ Creating 4 Bank Branches...")
        
        # HDFC Bank Central Mumbai Branch
        org1 = Organization(
            id=str(uuid.uuid4()),
            name="HDFC Bank Central Mumbai Branch",
            slug="hdfc-central-mumbai",
            description="HDFC Bank's flagship branch in Central Mumbai financial district",
            tenant_id=tenant1.id,
            join_token=f"HDFC-CENTRAL-{str(uuid.uuid4())[:8].upper()}",
            default_role="org_member",
            is_active=True,
            created_by=tenant_admin1.id,
            created_at=datetime.utcnow()
        )
        session.add(org1)
        
        # HDFC Bank Mumbai BKC Branch
        org2 = Organization(
            id=str(uuid.uuid4()),
            name="HDFC Bank Mumbai BKC Branch",
            slug="hdfc-bkc-mumbai",
            description="HDFC Bank's premium branch in Bandra Kurla Complex",
            tenant_id=tenant1.id,
            join_token=f"HDFC-BKC-{str(uuid.uuid4())[:8].upper()}",
            default_role="org_member",
            is_active=True,
            created_by=tenant_admin1.id,
            created_at=datetime.utcnow()
        )
        session.add(org2)
        
        # ICICI Bank Nariman Point Branch
        org3 = Organization(
            id=str(uuid.uuid4()),
            name="ICICI Bank Nariman Point Branch",
            slug="icici-nariman-point",
            description="ICICI Bank's corporate branch in Nariman Point business district",
            tenant_id=tenant2.id,
            join_token=f"ICICI-NARIMAN-{str(uuid.uuid4())[:8].upper()}",
            default_role="org_member",
            is_active=True,
            created_by=tenant_admin2.id,
            created_at=datetime.utcnow()
        )
        session.add(org3)
        
        # ICICI Bank Andheri Branch
        org4 = Organization(
            id=str(uuid.uuid4()),
            name="ICICI Bank Andheri Branch",
            slug="icici-andheri",
            description="ICICI Bank's retail branch in Andheri business hub",
            tenant_id=tenant2.id,
            join_token=f"ICICI-ANDHERI-{str(uuid.uuid4())[:8].upper()}",
            default_role="org_member",
            is_active=True,
            created_by=tenant_admin2.id,
            created_at=datetime.utcnow()
        )
        session.add(org4)
        session.flush()
        
        # ============================
        # 5. BRANCH MANAGERS (4 org admins)
        # ============================
        print("👨‍💻 Creating 4 Branch Managers...")
        
        # Org Admin 1 for HDFC Central Mumbai
        org_admin1 = User(
            id=str(uuid.uuid4()),
            email="manager.central@hdfcbank.com",
            username="hdfc_central_manager",
            hashed_password=pwd_context.hash("HdfcCentralManager123!"),
            full_name="Rajesh Patel - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=org1.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org_admin1)
        
        # Org Admin 2 for HDFC Mumbai BKC
        org_admin2 = User(
            id=str(uuid.uuid4()),
            email="manager.bkc@hdfcbank.com",
            username="hdfc_bkc_manager",
            hashed_password=pwd_context.hash("HdfcBkcManager123!"),
            full_name="Anita Desai - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=org2.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org_admin2)
        
        # Org Admin 3 for ICICI Nariman Point
        org_admin3 = User(
            id=str(uuid.uuid4()),
            email="manager.nariman@icicibank.com",
            username="icici_nariman_manager",
            hashed_password=pwd_context.hash("IciciNarimanManager123!"),
            full_name="Deepak Verma - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=org3.id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(org_admin3)
        
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
        # 6. BANK EMPLOYEES (8 org members)
        # ============================
        print("👥 Creating 8 Bank Employees...")
        
        # HDFC Central Mumbai employees
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
        
        # HDFC BKC employees
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
        
        # ICICI Nariman Point employees
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
        
        # ICICI Andheri employees
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
        # 7. INDEPENDENT USERS (2)
        # ============================
        print("👤 Creating 2 Independent Users...")
        
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
        # 8. SAMPLE COMPANIES
        # ============================
        print("🏭 Creating Sample Companies...")
        
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
                organization_id=None,
                is_global=True,
                created_by=super_admin.id,
                created_at=datetime.utcnow()
            )
            session.add(company)
        
        # Commit all changes
        session.commit()
        print("✅ All data created successfully!")
        
        return {
            'super_admin': super_admin,
            'tenant1': tenant1,
            'tenant2': tenant2,
            'tenant_admin1': tenant_admin1,
            'tenant_admin2': tenant_admin2,
            'org1': org1,
            'org2': org2,
            'org3': org3,
            'org4': org4,
            'org_admin1': org_admin1,
            'org_admin2': org_admin2,
            'org_admin3': org_admin3,
            'org_admin4': org_admin4,
            'hdfc_central_member1': hdfc_central_member1,
            'hdfc_central_member2': hdfc_central_member2,
            'hdfc_bkc_member1': hdfc_bkc_member1,
            'hdfc_bkc_member2': hdfc_bkc_member2,
            'icici_nariman_member1': icici_nariman_member1,
            'icici_nariman_member2': icici_nariman_member2,
            'icici_andheri_member1': icici_andheri_member1,
            'icici_andheri_member2': icici_andheri_member2,
            'user1': user1,
            'user2': user2
        }
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating data: {str(e)}")
        raise
    finally:
        session.close()

def print_setup_summary(data):
    """Print detailed summary of created data"""
    print("\n" + "="*80)
    print("📊 COMPLETE BANKING ROLE HIERARCHY SETUP SUMMARY")
    print("="*80)
    
    print(f"\n👑 SUPER ADMIN (1):")
    print(f"   Email: {data['super_admin'].email}")
    print(f"   Username: {data['super_admin'].username}")
    print(f"   Password: SuperAdmin123!")
    print(f"   Role: {data['super_admin'].role}")
    
    print(f"\n🏢 BANK TENANTS (2):")
    print(f"   1. {data['tenant1'].name} (slug: {data['tenant1'].slug})")
    print(f"   2. {data['tenant2'].name} (slug: {data['tenant2'].slug})")
    
    print(f"\n👨‍💼 BANK ADMINISTRATORS (2):")
    print(f"   1. {data['tenant_admin1'].email} (password: HdfcBankAdmin123!)")
    print(f"      Username: {data['tenant_admin1'].username}")
    print(f"      Role: {data['tenant_admin1'].role}")
    print(f"      Tenant: {data['tenant1'].name}")
    print(f"")
    print(f"   2. {data['tenant_admin2'].email} (password: IciciBankAdmin123!)")
    print(f"      Username: {data['tenant_admin2'].username}")
    print(f"      Role: {data['tenant_admin2'].role}")
    print(f"      Tenant: {data['tenant2'].name}")
    
    print(f"\n🏛️ BANK BRANCHES (4):")
    print(f"   1. {data['org1'].name} (in {data['tenant1'].name})")
    print(f"      Slug: {data['org1'].slug}")
    print(f"      Join Token: {data['org1'].join_token}")
    print(f"")
    print(f"   2. {data['org2'].name} (in {data['tenant1'].name})")
    print(f"      Slug: {data['org2'].slug}")
    print(f"      Join Token: {data['org2'].join_token}")
    print(f"")
    print(f"   3. {data['org3'].name} (in {data['tenant2'].name})")
    print(f"      Slug: {data['org3'].slug}")
    print(f"      Join Token: {data['org3'].join_token}")
    print(f"")
    print(f"   4. {data['org4'].name} (in {data['tenant2'].name})")
    print(f"      Slug: {data['org4'].slug}")
    print(f"      Join Token: {data['org4'].join_token}")
    
    print(f"\n👨‍💻 BRANCH MANAGERS (4):")
    print(f"   1. {data['org_admin1'].email} (password: HdfcCentralManager123!)")
    print(f"      Username: {data['org_admin1'].username}")
    print(f"      Role: {data['org_admin1'].role}")
    print(f"      Organization: {data['org1'].name}")
    print(f"")
    print(f"   2. {data['org_admin2'].email} (password: HdfcBkcManager123!)")
    print(f"      Username: {data['org_admin2'].username}")
    print(f"      Role: {data['org_admin2'].role}")
    print(f"      Organization: {data['org2'].name}")
    print(f"")
    print(f"   3. {data['org_admin3'].email} (password: IciciNarimanManager123!)")
    print(f"      Username: {data['org_admin3'].username}")
    print(f"      Role: {data['org_admin3'].role}")
    print(f"      Organization: {data['org3'].name}")
    print(f"")
    print(f"   4. {data['org_admin4'].email} (password: IciciAndheriManager123!)")
    print(f"      Username: {data['org_admin4'].username}")
    print(f"      Role: {data['org_admin4'].role}")
    print(f"      Organization: {data['org4'].name}")
    
    print(f"\n👥 BANK EMPLOYEES (8):")
    print(f"   HDFC Bank Central Mumbai Branch:")
    print(f"   1. {data['hdfc_central_member1'].email} (password: RohanHdfc123!)")
    print(f"      Username: {data['hdfc_central_member1'].username}")
    print(f"      Role: {data['hdfc_central_member1'].role}")
    print(f"")
    print(f"   2. {data['hdfc_central_member2'].email} (password: KavyaHdfc123!)")
    print(f"      Username: {data['hdfc_central_member2'].username}")
    print(f"      Role: {data['hdfc_central_member2'].role}")
    print(f"")
    print(f"   HDFC Bank Mumbai BKC Branch:")
    print(f"   3. {data['hdfc_bkc_member1'].email} (password: ArjunHdfc123!)")
    print(f"      Username: {data['hdfc_bkc_member1'].username}")
    print(f"      Role: {data['hdfc_bkc_member1'].role}")
    print(f"")
    print(f"   4. {data['hdfc_bkc_member2'].email} (password: NehaHdfc123!)")
    print(f"      Username: {data['hdfc_bkc_member2'].username}")
    print(f"      Role: {data['hdfc_bkc_member2'].role}")
    print(f"")
    print(f"   ICICI Bank Nariman Point Branch:")
    print(f"   5. {data['icici_nariman_member1'].email} (password: VikramIcici123!)")
    print(f"      Username: {data['icici_nariman_member1'].username}")
    print(f"      Role: {data['icici_nariman_member1'].role}")
    print(f"")
    print(f"   6. {data['icici_nariman_member2'].email} (password: RituIcici123!)")
    print(f"      Username: {data['icici_nariman_member2'].username}")
    print(f"      Role: {data['icici_nariman_member2'].role}")
    print(f"")
    print(f"   ICICI Bank Andheri Branch:")
    print(f"   7. {data['icici_andheri_member1'].email} (password: AdityaIcici123!)")
    print(f"      Username: {data['icici_andheri_member1'].username}")
    print(f"      Role: {data['icici_andheri_member1'].role}")
    print(f"")
    print(f"   8. {data['icici_andheri_member2'].email} (password: PoojaIcici123!)")
    print(f"      Username: {data['icici_andheri_member2'].username}")
    print(f"      Role: {data['icici_andheri_member2'].role}")
    
    print(f"\n👤 INDEPENDENT USERS (2):")
    print(f"   1. {data['user1'].email} (password: Consultant123!)")
    print(f"      Username: {data['user1'].username}")
    print(f"      Role: {data['user1'].role}")
    print(f"")
    print(f"   2. {data['user2'].email} (password: Analyst123!)")
    print(f"      Username: {data['user2'].username}")
    print(f"      Role: {data['user2'].role}")
    
    print(f"\n🏭 SAMPLE COMPANIES:")
    print(f"   - AAPL: Apple Inc.")
    print(f"   - MSFT: Microsoft Corporation")
    print(f"   - GOOGL: Alphabet Inc.")
    print(f"   - AMZN: Amazon.com Inc.")
    print(f"   - TSLA: Tesla Inc.")
    
    print(f"\n🔐 BANKING 5-ROLE HIERARCHY:")
    print(f"   1. super_admin - System administrator (pranitsuperadmin@gmail.com)")
    print(f"   2. tenant_admin - Bank-wide administrator (manages all branches)")
    print(f"   3. org_admin - Branch manager (manages branch employees)")
    print(f"   4. org_member - Bank employee (branch-specific access)")
    print(f"   5. user - Independent user (no organizational affiliation)")
    
    print(f"\n🏦 PROFESSIONAL BANKING SETUP:")
    print(f"   - 2 Major Indian Banks: HDFC Bank Limited & ICICI Bank Limited")
    print(f"   - 4 Mumbai Branches: Central Mumbai, BKC, Nariman Point, Andheri")
    print(f"   - 16 Total Users: 1 Super Admin + 2 Bank Admins + 4 Branch Managers + 8 Bank Employees + 2 Independent Users")
    print(f"   - Realistic professional emails and Indian names")
    
    print(f"\n✅ Professional Banking Setup completed successfully!")
    print(f"🚀 You can now start the API server and test all role-based functionality")
    print("="*80)

def main():
    """Main function to setup data"""
    try:
        print("🎯 Setting up complete role hierarchy for Default Rate Prediction System...")
        
        # Setup all data
        data = setup_complete_role_hierarchy()
        
        # Print summary
        print_setup_summary(data)
        
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        raise

if __name__ == "__main__":
    main()
