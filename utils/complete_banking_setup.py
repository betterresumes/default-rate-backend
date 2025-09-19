#!/usr/bin/env python3
"""
Complete the banking setup - add organizations, branch managers, and employees
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

from app.core.database import User, Tenant, Organization, Company

# Database setup - using direct DATABASE_URL
DATABASE_URL = "postgresql://neondb_owner:npg_2ZLE4VuBytOa@ep-crimson-cell-adrxvu8a-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Password hashing context (faster rounds for development)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

def complete_banking_setup():
    """Complete the banking hierarchy setup"""
    session = SessionLocal()
    
    try:
        print("🎯 Completing Banking Hierarchy Setup...")
        
        # Get existing data
        super_admin = session.query(User).filter(User.email == "pranitsuperadmin@gmail.com").first()
        hdfc_tenant = session.query(Tenant).filter(Tenant.slug == "hdfc-bank").first()
        icici_tenant = session.query(Tenant).filter(Tenant.slug == "icici-bank").first()
        hdfc_admin = session.query(User).filter(User.email == "admin@hdfcbank.com").first()
        icici_admin = session.query(User).filter(User.email == "admin@icicibank.com").first()
        
        if not all([super_admin, hdfc_tenant, icici_tenant, hdfc_admin, icici_admin]):
            print("❌ Required base data not found. Please run reset_db_safe.py first.")
            return
        
        print(f"✅ Found existing data: {super_admin.email}, {hdfc_tenant.name}, {icici_tenant.name}")
        
        # ============================
        # 1. CREATE BANK BRANCH ORGANIZATIONS
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
        session.commit()  # Commit to get organization IDs
        
        # ============================
        # 2. CREATE BRANCH MANAGERS (ORG ADMINS)
        # ============================
        print("👨‍💻 Creating 4 Branch Managers...")
        
        managers_data = [
            {
                "email": "manager.central@hdfcbank.com",
                "username": "hdfc_central_manager",
                "password": "HdfcCentralManager123!",
                "full_name": "Amit Patel - Branch Manager",
                "org_id": hdfc_central.id
            },
            {
                "email": "manager.bkc@hdfcbank.com",
                "username": "hdfc_bkc_manager",
                "password": "HdfcBkcManager123!",
                "full_name": "Sunita Desai - Branch Manager",
                "org_id": hdfc_bkc.id
            },
            {
                "email": "manager.nariman@icicibank.com",
                "username": "icici_nariman_manager",
                "password": "IciciNarimanManager123!",
                "full_name": "Rahul Singh - Branch Manager",
                "org_id": icici_nariman.id
            },
            {
                "email": "manager.andheri@icicibank.com",
                "username": "icici_andheri_manager",
                "password": "IciciAndheriManager123!",
                "full_name": "Sneha Gupta - Branch Manager",
                "org_id": icici_andheri.id
            }
        ]
        
        managers = []
        for mgr_data in managers_data:
            manager = User(
                email=mgr_data["email"],
                username=mgr_data["username"],
                hashed_password=pwd_context.hash(mgr_data["password"]),
                full_name=mgr_data["full_name"],
                role="org_admin",
                tenant_id=None,
                organization_id=mgr_data["org_id"],
                is_active=True
            )
            session.add(manager)
            managers.append(manager)
        
        session.commit()
        
        # ============================
        # 3. CREATE BANK EMPLOYEES (ORG MEMBERS)
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
        # 4. CREATE INDEPENDENT USERS
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
        # 5. CREATE SAMPLE COMPANIES
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
        print("✅ Banking hierarchy completed successfully!")
        
        # Print summary
        total_users = session.query(User).count()
        total_orgs = session.query(Organization).count()
        total_companies = session.query(Company).count()
        
        print(f"\n📊 FINAL SUMMARY:")
        print(f"   👥 Total Users: {total_users}")
        print(f"   🏛️ Total Organizations: {total_orgs}")
        print(f"   🏭 Total Companies: {total_companies}")
        print(f"   🏢 Total Tenants: 2 (HDFC & ICICI Banks)")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error completing setup: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    complete_banking_setup()
