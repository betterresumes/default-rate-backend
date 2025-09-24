#!/usr/bin/env python3
"""
Usage:
    python scripts/setup_application_data.py
"""

import os
import sys
import logging
import secrets
import string
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

sys.path.insert(0, str(backend_dir))


DATABASE_URL = "postgresql://neondb_owner:npg_FRS5ptsg3QcE@ep-snowy-darkness-adw0r2ai-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def get_session_local():
    """Create database session using the specific DATABASE_URL"""
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal

try:
    from app.core.database import User, Tenant, Organization, OrganizationMemberWhitelist, Company
    from sqlalchemy import text
    logger.info("✅ Successfully imported database components")
except ImportError as e:
    logger.error(f"❌ Failed to import database components: {e}")
    sys.exit(1)

DATA_CONFIG1 = {
    "super_admin": {
        "email": "admin@defaultrate.com",
        "username": "super_admin",
        "password": "SuperAdmin123!",
        "full_name": "Rajesh Kumar Sharma",
        "role": "super_admin"
    },
    
    "tenant": {
        "name": "HDFC Bank Limited",
        "slug": "hdfc-bank",
        "domain": "hdfcbank.com",
        "description": "India's leading private sector bank"
    },
    
    "tenant_admin": {
        "email": "admin@hdfcbank.com",
        "username": "tenant_admin",
        "password": "TenantAdmin123!",
        "full_name": "Priya Gupta",
        "role": "tenant_admin"
    },
    
    "organizations": [
        {
            "name": "Credit Risk Management Division",
            "slug": "credit-risk-management",
            "domain": "risk.hdfcbank.com",
            "description": "Advanced credit risk assessment and default prediction analytics for retail and corporate banking",
            "default_role": "org_member",
            
            "admin": {
                "email": "risk.head@hdfcbank.com",
                "username": "risk_head",
                "password": "RiskHead123!",
                "full_name": "Dr. Amit Krishnamurthy",
                "role": "org_admin"
            },
            
            "members": [
                {
                    "email": "senior.analyst@hdfcbank.com",
                    "username": "senior_risk_analyst",
                    "password": "SeniorAnalyst123!",
                    "full_name": "Sneha Raghavan Nair",
                    "role": "org_member"
                },
                {
                    "email": "quant.analyst@hdfcbank.com",
                    "username": "quant_analyst", 
                    "password": "QuantAnalyst123!",
                    "full_name": "Arjun Vikram Singh",
                    "role": "org_member"
                }
            ]
        },
        {
            "name": "Data Analytics & Machine Learning",
            "slug": "data-analytics-ml",
            "domain": "analytics.hdfcbank.com",
            "description": "Machine learning models and statistical analysis for financial risk prediction and business intelligence",
            "default_role": "org_member",
            
            "admin": {
                "email": "analytics.head@hdfcbank.com",
                "username": "analytics_head",
                "password": "AnalyticsHead123!",
                "full_name": "Dr. Kavitha Subramanian",
                "role": "org_admin"
            },
            
            "members": [
                {
                    "email": "data.scientist@hdfcbank.com",
                    "username": "data_scientist_lead",
                    "password": "DataScientist123!",
                    "full_name": "Rohit Agarwal Joshi",
                    "role": "org_member"
                },
                {
                    "email": "ml.engineer@hdfcbank.com",
                    "username": "ml_engineer",
                    "password": "MLEngineer123!",
                    "full_name": "Ananya Sharma Reddy",
                    "role": "org_member"
                }
            ]
        }
    ]
}

DATA_CONFIG = {
    "super_admin": {
        "email": "admin2@defaultrate.com",
        "username": "RajeshKSharma",
        "password": "SuperAdmin123!",
        "full_name": "Rajesh Kumar Sharma",
        "role": "super_admin"
    },
    
    "tenant": {
        "name": "ICICI Bank Limited",
        "slug": "icici-bank",
        "domain": "icicibank.com",
        "description": "India's largest private sector bank by consolidated assets offering comprehensive banking and financial services"
    },
    
    "tenant_admin": {
        "email": "admin@icicibank.com",
        "username": "tenant_admin_icici",
        "password": "TenantAdmin123!",
        "full_name": "Deepika Agarwal Sharma",
        "role": "tenant_admin"
    },
    
    "organizations": [
        {
            "name": "Corporate Credit & Risk Assessment",
            "slug": "corporate-credit-risk",
            "domain": "corporate.icicibank.com",
            "description": "Corporate lending and credit risk evaluation for large enterprises and institutional clients",
            "default_role": "org_member",
            
            "admin": {
                "email": "corporate.head@icicibank.com",
                "username": "corporate_head",
                "password": "CorporateHead123!",
                "full_name": "Dr. Ramesh Chandra Verma",
                "role": "org_admin"
            },
            
            "members": [
                {
                    "email": "credit.manager@icicibank.com",
                    "username": "credit_manager",
                    "password": "CreditManager123!",
                    "full_name": "Meera Krishnan Iyer",
                    "role": "org_member"
                },
                {
                    "email": "risk.specialist@icicibank.com",
                    "username": "risk_specialist", 
                    "password": "RiskSpecialist123!",
                    "full_name": "Vivek Kumar Agarwal",
                    "role": "org_member"
                }
            ]
        },
        {
            "name": "Retail Banking & Consumer Finance",
            "slug": "retail-consumer-finance",
            "domain": "retail.icicibank.com",
            "description": "Personal banking, home loans, and consumer credit risk assessment division",
            "default_role": "org_member",
            
            "admin": {
                "email": "retail.director@icicibank.com",
                "username": "retail_director",
                "password": "RetailDirector123!",
                "full_name": "Dr. Sunita Rajesh Patel",
                "role": "org_admin"
            },
            
            "members": [
                {
                    "email": "loan.officer@icicibank.com",
                    "username": "loan_officer_lead",
                    "password": "LoanOfficer123!",
                    "full_name": "Karthik Venkatesh Rao",
                    "role": "org_member"
                },
                {
                    "email": "consumer.analyst@icicibank.com",
                    "username": "consumer_analyst",
                    "password": "ConsumerAnalyst123!",
                    "full_name": "Pooja Sharma Malhotra",
                    "role": "org_member"
                }
            ]
        }
    ]
}

def generate_join_token():
    """Generate a secure join token"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

def create_user(db, user_data, tenant_id=None, organization_id=None):
    """Create a user with the specified data"""
    try:
        hashed_password = pwd_context.hash(user_data["password"])
        
        user = User(
            email=user_data["email"],
            username=user_data["username"],
            hashed_password=hashed_password,
            full_name=user_data["full_name"],
            role=user_data["role"],
            tenant_id=tenant_id,
            organization_id=organization_id,
            is_active=True,
            created_at=datetime.now()
        )
        
        db.add(user)
        db.flush()  
        
        logger.info(f"✅ Created user: {user_data['full_name']} ({user_data['email']})")
        return user
        
    except Exception as e:
        logger.error(f"❌ Failed to create user {user_data['email']}: {e}")
        raise

def create_super_admin(db):
    """Create the super admin user"""
    logger.info("👑 Creating Super Admin...")
    
    admin_data = DATA_CONFIG["super_admin"]
    user = create_user(db, admin_data)
    
    logger.info(f"👑 Super Admin created successfully: {admin_data['email']}")
    return user

def create_tenant_with_admin(db, super_admin_id):
    """Create tenant and tenant admin"""
    logger.info("🏢 Creating Tenant...")
    
    # Create tenant
    tenant_data = DATA_CONFIG["tenant"]
    tenant = Tenant(
        name=tenant_data["name"],
        slug=tenant_data["slug"],
        domain=tenant_data["domain"],
        description=tenant_data["description"],
        is_active=True,
        created_by=super_admin_id,
        created_at=datetime.now()
    )
    
    db.add(tenant)
    db.flush()
    
    logger.info(f"✅ Tenant created: {tenant_data['name']}")
    
    # Create tenant admin
    logger.info("👔 Creating Tenant Admin...")
    admin_data = DATA_CONFIG["tenant_admin"]
    tenant_admin = create_user(db, admin_data, tenant_id=tenant.id)
    
    logger.info(f"👔 Tenant Admin created: {admin_data['email']}")
    return tenant, tenant_admin

def create_organization_with_users(db, org_config, tenant_id, tenant_admin_id):
    """Create organization with admin and members"""
    logger.info(f"🏛️  Creating Organization: {org_config['name']}")
    
    # Create organization
    organization = Organization(
        tenant_id=tenant_id,
        name=org_config["name"],
        slug=org_config["slug"],
        domain=org_config["domain"],
        description=org_config["description"],
        join_token=generate_join_token(),
        join_enabled=True,
        default_role=org_config["default_role"],
        max_users=500,
        is_active=True,
        allow_global_data_access=False,  # Default to False for new organizations
        created_by=tenant_admin_id,
        created_at=datetime.now()
    )
    
    db.add(organization)
    db.flush()
    
    logger.info(f"✅ Organization created: {org_config['name']}")
    logger.info(f"🔗 Join token: {organization.join_token}")
    
    # Create organization admin
    logger.info(f"👨‍💼 Creating Organization Admin...")
    admin_data = org_config["admin"]
    org_admin = create_user(db, admin_data, organization_id=organization.id)
    
    # Add admin to whitelist
    whitelist_entry = OrganizationMemberWhitelist(
        organization_id=organization.id,
        email=admin_data["email"],
        added_by=tenant_admin_id,
        added_at=datetime.now(),
        status="active"
    )
    db.add(whitelist_entry)
    
    # Create organization members
    logger.info(f"👥 Creating Organization Members...")
    members = []
    for member_data in org_config["members"]:
        member = create_user(db, member_data, organization_id=organization.id)
        members.append(member)
        
        # Add member to whitelist
        whitelist_entry = OrganizationMemberWhitelist(
            organization_id=organization.id,
            email=member_data["email"],
            added_by=org_admin.id,
            added_at=datetime.now(),
            status="active"
        )
        db.add(whitelist_entry)
    
    logger.info(f"✅ Organization setup complete: {len(org_config['members'])} members created")
    return organization, org_admin, members

def setup_application_data():
    """Main function to set up all application data"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        logger.info("🚀 Starting application data setup...")
        
        # Create Super Admin
        super_admin = create_super_admin(db)
        
        # Create Tenant with Tenant Admin
        tenant, tenant_admin = create_tenant_with_admin(db, super_admin.id)
        
        # Create Organizations with users
        organizations_data = []
        for org_config in DATA_CONFIG["organizations"]:
            org, admin, members = create_organization_with_users(
                db, org_config, tenant.id, tenant_admin.id
            )
            organizations_data.append({
                "organization": org,
                "admin": admin,
                "members": members
            })
        
        # Commit all changes
        db.commit()
        logger.info("💾 All data committed to database")
        
        # Print summary
        print_setup_summary(super_admin, tenant, tenant_admin, organizations_data)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

def print_setup_summary(super_admin, tenant, tenant_admin, organizations_data):
    """Print a comprehensive summary of created data"""
    logger.info("\n" + "=" * 70)
    logger.info("🎉 APPLICATION SETUP COMPLETED SUCCESSFULLY!")
    logger.info("=" * 70)
    
    print("\n📋 SETUP SUMMARY:")
    print(f"📊 Total Users Created: {1 + 1 + len(organizations_data) * 3}")  # super + tenant_admin + (admin + 2 members) * orgs
    print(f"🏢 Tenants Created: 1")
    print(f"🏛️  Organizations Created: {len(organizations_data)}")
    
    print("\n👑 SUPER ADMIN:")
    print(f"   📧 Email: {super_admin.email}")
    print(f"   👤 Username: {super_admin.username}")
    print(f"   🔑 Password: {DATA_CONFIG['super_admin']['password']}")
    print(f"   🏷️  Role: {super_admin.role}")
    print(f"   👨‍💼 Full Name: {super_admin.full_name}")
    
    print(f"\n🏢 TENANT: {tenant.name}")
    print(f"   🌐 Domain: {tenant.domain}")
    print(f"   📝 Description: {tenant.description}")
    
    print(f"\n👔 TENANT ADMIN:")
    print(f"   📧 Email: {tenant_admin.email}")
    print(f"   👤 Username: {tenant_admin.username}")
    print(f"   🔑 Password: {DATA_CONFIG['tenant_admin']['password']}")
    print(f"   🏷️  Role: {tenant_admin.role}")
    print(f"   👨‍💼 Full Name: {tenant_admin.full_name}")
    
    for i, org_data in enumerate(organizations_data, 1):
        org = org_data["organization"]
        admin = org_data["admin"]
        members = org_data["members"]
        
        print(f"\n🏛️  ORGANIZATION {i}: {org.name}")
        print(f"   🌐 Domain: {org.domain}")
        print(f"   🔗 Join Token: {org.join_token}")
        print(f"   📝 Description: {org.description}")
        
        print(f"\n   👨‍💼 ORGANIZATION ADMIN:")
        print(f"      📧 Email: {admin.email}")
        print(f"      👤 Username: {admin.username}")
        print(f"      🔑 Password: {[org_conf for org_conf in DATA_CONFIG['organizations'] if org_conf['name'] == org.name][0]['admin']['password']}")
        print(f"      👨‍💼 Full Name: {admin.full_name}")
        
        print(f"\n   👥 ORGANIZATION MEMBERS:")
        for j, member in enumerate(members, 1):
            member_config = [org_conf for org_conf in DATA_CONFIG['organizations'] if org_conf['name'] == org.name][0]['members'][j-1]
            print(f"      {j}. {member.full_name}")
            print(f"         📧 Email: {member.email}")
            print(f"         👤 Username: {member.username}")
            print(f"         🔑 Password: {member_config['password']}")
    
    print("\n✅ NEXT STEPS:")
    print("1. 🚀 Start your FastAPI application server")
    print("2. 📬 Import the API collection for testing")
    print("3. 🔐 Use the login credentials above to test authentication")
    print("4. 🧪 Test the API endpoints with different user roles")
    print("5. 🏭 Create companies and predictions via the API")
    
    print("\n📝 NOTES:")
    print("- All passwords follow strong security practices")
    print("- Email addresses use professional domain names")
    print("- Users are properly assigned to their respective organizations")
    print("- Whitelist entries created for all organization members")
    print("- Join tokens generated for organization access")
    print("- Companies can be created via the API endpoints")

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🏗️  Default Rate Prediction System - Data Setup")
    logger.info("=" * 60)
    
    # Verify database is ready
    try:
        SessionLocal = get_session_local()
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection verified")
        logger.info(f"🔗 Using Database: {DATABASE_URL[:50]}...{DATABASE_URL[-20:]}")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("Please check the database connection details")
        sys.exit(1)
    
    # Setup data
    success = setup_application_data()
    
    if not success:
        logger.error("❌ Application data setup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
