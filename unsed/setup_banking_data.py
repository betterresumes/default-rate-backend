#!/usr/bin/env python3
"""
Professional Banking Setup Data for Default Rate Prediction System
Creates a complete role hierarchy with HDFC Bank and ICICI Bank branches
"""

import os
import sys
import secrets
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

# Password hashing context (faster rounds for development)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

def setup_banking_hierarchy():
    """Setup complete professional banking role hierarchy"""
    session = SessionLocal()
    
    try:
        print("🎯 Setting up Professional Banking Role Hierarchy...")
        
        # ============================
        # 1. SUPER ADMIN
        # ============================
        print("👑 Creating Super Admin...")
        super_admin = User(
            email="pranitsuperadmin@gmail.com",
            username="super_admin",
            hashed_password=pwd_context.hash("SuperAdmin123!"),
            full_name="Pranit Patil - System Administrator",
            role="super_admin",
            tenant_id=None,
            organization_id=None,
            is_active=True
        )
        session.add(super_admin)
        session.commit()  # Commit to get the ID
        
        # ============================
        # 2. BANK TENANTS
        # ============================
        print("🏢 Creating 2 Major Indian Bank Tenants...")
        
        # HDFC Bank Tenant
        hdfc_tenant = Tenant(
            name="HDFC Bank Limited",
            slug="hdfc-bank",
            domain="hdfcbank.com",
            description="One of India's leading private sector banks",
            is_active=True,
            created_by=super_admin.id
        )
        session.add(hdfc_tenant)
        
        # ICICI Bank Tenant
        icici_tenant = Tenant(
            name="ICICI Bank Limited",
            slug="icici-bank",
            domain="icicibank.com",
            description="India's largest private sector bank by market capitalization",
            is_active=True,
            created_by=super_admin.id
        )
        session.add(icici_tenant)
        session.commit()  # Commit to get tenant IDs
        
        # ============================
        # 3. TENANT ADMINS
        # ============================
        print("👨‍💼 Creating 2 Bank Administrators...")
        
        # HDFC Bank Admin
        hdfc_admin = User(
            email="admin@hdfcbank.com",
            username="hdfc_bank_admin",
            hashed_password=pwd_context.hash("HdfcBankAdmin123!"),
            full_name="Rajesh Kumar - HDFC Bank IT Head",
            role="tenant_admin",
            tenant_id=hdfc_tenant.id,
            organization_id=None,
            is_active=True
        )
        session.add(hdfc_admin)
        
        # ICICI Bank Admin
        icici_admin = User(
            email="admin@icicibank.com",
            username="icici_bank_admin",
            hashed_password=pwd_context.hash("IciciBankAdmin123!"),
            full_name="Priya Sharma - ICICI Bank Operations Head",
            role="tenant_admin",
            tenant_id=icici_tenant.id,
            organization_id=None,
            is_active=True
        )
        session.add(icici_admin)
        session.commit()
        
        # ============================
        # 4. BANK BRANCH ORGANIZATIONS
        # ============================
        print("🏛️ Creating 4 Bank Branch Organizations...")
        
        # HDFC Branches
        hdfc_central = Organization(
            tenant_id=hdfc_tenant.id,
            name="HDFC Bank Mumbai Central Branch",
            slug="hdfc-mumbai-central",
            description="HDFC Bank flagship branch in Mumbai Central",
            join_token=secrets.token_hex(16),
            is_active=True,
            default_role="org_member",
            created_by=hdfc_admin.id
        )
        session.add(hdfc_central)
        
        hdfc_bkc = Organization(
            tenant_id=hdfc_tenant.id,
            name="HDFC Bank Mumbai BKC Branch",
            slug="hdfc-mumbai-bkc",
            description="HDFC Bank branch in Bandra Kurla Complex",
            join_token=secrets.token_hex(16),
            is_active=True,
            default_role="org_member",
            created_by=hdfc_admin.id
        )
        session.add(hdfc_bkc)
        
        # ICICI Branches
        icici_nariman = Organization(
            tenant_id=icici_tenant.id,
            name="ICICI Bank Nariman Point Branch",
            slug="icici-nariman-point",
            description="ICICI Bank premium branch at Nariman Point",
            join_token=secrets.token_hex(16),
            is_active=True,
            default_role="org_member",
            created_by=icici_admin.id
        )
        session.add(icici_nariman)
        
        icici_andheri = Organization(
            tenant_id=icici_tenant.id,
            name="ICICI Bank Andheri Branch",
            slug="icici-andheri",
            description="ICICI Bank branch in Andheri West",
            join_token=secrets.token_hex(16),
            is_active=True,
            default_role="org_member",
            created_by=icici_admin.id
        )
        session.add(icici_andheri)
        session.commit()
        
        # ============================
        # 5. BRANCH MANAGERS (ORG ADMINS)
        # ============================
        print("👨‍💻 Creating 4 Branch Managers...")
        
        # HDFC Branch Managers
        hdfc_central_manager = User(
            email="manager.central@hdfcbank.com",
            username="hdfc_central_manager",
            hashed_password=pwd_context.hash("HdfcCentralManager123!"),
            full_name="Amit Patel - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=hdfc_central.id,
            is_active=True
        )
        session.add(hdfc_central_manager)
        
        hdfc_bkc_manager = User(
            email="manager.bkc@hdfcbank.com",
            username="hdfc_bkc_manager",
            hashed_password=pwd_context.hash("HdfcBkcManager123!"),
            full_name="Sunita Desai - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=hdfc_bkc.id,
            is_active=True
        )
        session.add(hdfc_bkc_manager)
        
        # ICICI Branch Managers
        icici_nariman_manager = User(
            email="manager.nariman@icicibank.com",
            username="icici_nariman_manager",
            hashed_password=pwd_context.hash("IciciNarimanManager123!"),
            full_name="Rahul Singh - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=icici_nariman.id,
            is_active=True
        )
        session.add(icici_nariman_manager)
        
        icici_andheri_manager = User(
            email="manager.andheri@icicibank.com",
            username="icici_andheri_manager",
            hashed_password=pwd_context.hash("IciciAndheriManager123!"),
            full_name="Sneha Gupta - Branch Manager",
            role="org_admin",
            tenant_id=None,
            organization_id=icici_andheri.id,
            is_active=True
        )
        session.add(icici_andheri_manager)
        session.commit()
        
        # ============================
        # 6. BANK EMPLOYEES (ORG MEMBERS)
        # ============================
        print("👥 Creating 8 Bank Employees...")
        
        employees_data = [
            # HDFC Central Branch
            {
                "email": "rohan.analyst@hdfcbank.com",
                "username": "rohan_hdfc_analyst",
                "password": "RohanHdfc123!",
                "full_name": "Rohan Singh - Risk Analyst",
                "org_id": hdfc_central.id
            },
            {
                "email": "kavya.officer@hdfcbank.com",
                "username": "kavya_hdfc_officer",
                "password": "KavyaHdfc123!",
                "full_name": "Kavya Nair - Credit Officer",
                "org_id": hdfc_central.id
            },
            # HDFC BKC Branch
            {
                "email": "arjun.advisor@hdfcbank.com",
                "username": "arjun_hdfc_advisor",
                "password": "ArjunHdfc123!",
                "full_name": "Arjun Mehta - Investment Advisor",
                "org_id": hdfc_bkc.id
            },
            {
                "email": "neha.specialist@hdfcbank.com",
                "username": "neha_hdfc_specialist",
                "password": "NehaHdfc123!",
                "full_name": "Neha Joshi - Treasury Specialist",
                "org_id": hdfc_bkc.id
            },
            # ICICI Nariman Point Branch
            {
                "email": "vikram.analyst@icicibank.com",
                "username": "vikram_icici_analyst",
                "password": "VikramIcici123!",
                "full_name": "Vikram Rao - Financial Analyst",
                "org_id": icici_nariman.id
            },
            {
                "email": "ritu.manager@icicibank.com",
                "username": "ritu_icici_manager",
                "password": "RituIcici123!",
                "full_name": "Ritu Agarwal - Portfolio Manager",
                "org_id": icici_nariman.id
            },
            # ICICI Andheri Branch
            {
                "email": "aditya.consultant@icicibank.com",
                "username": "aditya_icici_consultant",
                "password": "AdityaIcici123!",
                "full_name": "Aditya Sharma - Wealth Consultant",
                "org_id": icici_andheri.id
            },
            {
                "email": "pooja.executive@icicibank.com",
                "username": "pooja_icici_executive",
                "password": "PoojaIcici123!",
                "full_name": "Pooja Reddy - Relationship Executive",
                "org_id": icici_andheri.id
            }
        ]
        
        employees = []
        for emp_data in employees_data:
            employee = User(
                email=emp_data["email"],
                username=emp_data["username"],
                hashed_password=pwd_context.hash(emp_data["password"]),
                full_name=emp_data["full_name"],
                role="org_member",
                tenant_id=None,
                organization_id=emp_data["org_id"],
                is_active=True
            )
            session.add(employee)
            employees.append(employee)
        
        # ============================
        # 7. INDEPENDENT USERS
        # ============================
        print("👤 Creating 2 Independent Users...")
        
        consultant = User(
            email="consultant@defaultrate.com",
            username="independent_consultant",
            hashed_password=pwd_context.hash("Consultant123!"),
            full_name="Rajiv Malhotra - Independent Consultant",
            role="user",
            tenant_id=None,
            organization_id=None,
            is_active=True
        )
        session.add(consultant)
        
        analyst = User(
            email="analyst@defaultrate.com",
            username="freelance_analyst",
            hashed_password=pwd_context.hash("Analyst123!"),
            full_name="Meera Iyer - Freelance Financial Analyst",
            role="user",
            tenant_id=None,
            organization_id=None,
            is_active=True
        )
        session.add(analyst)
        
        # ============================
        # 8. SAMPLE COMPANIES
        # ============================
        print("🏭 Creating Sample Companies...")
        
        companies_data = [
            {"symbol": "AAPL", "name": "Apple Inc.", "market_cap": 3000000000000, "sector": "Technology"},
            {"symbol": "MSFT", "name": "Microsoft Corporation", "market_cap": 2800000000000, "sector": "Technology"},
            {"symbol": "GOOGL", "name": "Alphabet Inc.", "market_cap": 1700000000000, "sector": "Technology"},
            {"symbol": "AMZN", "name": "Amazon.com Inc.", "market_cap": 1500000000000, "sector": "Consumer Services"},
            {"symbol": "TSLA", "name": "Tesla Inc.", "market_cap": 800000000000, "sector": "Consumer Goods"}
        ]
        
        for comp_data in companies_data:
            company = Company(
                symbol=comp_data["symbol"],
                name=comp_data["name"],
                market_cap=comp_data["market_cap"],
                sector=comp_data["sector"],
                organization_id=None,  # Global company
                is_global=True,
                created_by=super_admin.id
            )
            session.add(company)
        
        # Final commit
        session.commit()
        print("✅ All banking data created successfully!")
        
        return {
            'super_admin': super_admin,
            'hdfc_tenant': hdfc_tenant,
            'icici_tenant': icici_tenant,
            'hdfc_admin': hdfc_admin,
            'icici_admin': icici_admin,
            'hdfc_central': hdfc_central,
            'hdfc_bkc': hdfc_bkc,
            'icici_nariman': icici_nariman,
            'icici_andheri': icici_andheri,
            'employees': employees,
            'consultant': consultant,
            'analyst': analyst
        }
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating banking data: {str(e)}")
        raise
    finally:
        session.close()

def print_banking_summary(data):
    """Print summary of created banking data"""
    print("\n" + "="*80)
    print("📊 PROFESSIONAL BANKING HIERARCHY SETUP SUMMARY")
    print("="*80)
    
    print(f"\n👑 SUPER ADMIN:")
    print(f"   Email: {data['super_admin'].email}")
    print(f"   Password: SuperAdmin123!")
    
    print(f"\n🏢 BANK TENANTS:")
    print(f"   1. {data['hdfc_tenant'].name}")
    print(f"   2. {data['icici_tenant'].name}")
    
    print(f"\n👨‍💼 TENANT ADMINS:")
    print(f"   1. {data['hdfc_admin'].email} (password: HdfcBankAdmin123!)")
    print(f"   2. {data['icici_admin'].email} (password: IciciBankAdmin123!)")
    
    print(f"\n🏛️ BANK BRANCHES (4):")
    print(f"   1. {data['hdfc_central'].name}")
    print(f"   2. {data['hdfc_bkc'].name}")
    print(f"   3. {data['icici_nariman'].name}")
    print(f"   4. {data['icici_andheri'].name}")
    
    print(f"\n👥 TOTAL USERS CREATED: {len(data['employees']) + 6}")
    print(f"   - 1 Super Admin")
    print(f"   - 2 Tenant Admins") 
    print(f"   - 4 Branch Managers")
    print(f"   - 8 Bank Employees")
    print(f"   - 2 Independent Users")
    
    print(f"\n🚀 Setup completed successfully!")
    print("="*80)

def main():
    """Main function to setup banking data"""
    try:
        print("🎯 Setting up Professional Banking Hierarchy...")
        
        # Setup all data
        data = setup_banking_hierarchy()
        
        # Print summary
        print_banking_summary(data)
        
    except Exception as e:
        print(f"❌ Error during setup: {str(e)}")
        raise

if __name__ == "__main__":
    main()
