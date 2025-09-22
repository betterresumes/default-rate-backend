#!/usr/bin/env python3
"""
Professional Application Data Setup Script for Default Rate Prediction System

This script creates a complete professional setup with:
- 1 Super Admin
- 1 Tenant with 1 Tenant Admin
- 2 Organizations with 1 Org Admin each
- 2 Org Members per organization
- Professional email addresses and company names

All data is configurable through the DATA_CONFIG dictionary.

Usage:
    python scripts/setup_application_data.py

Requirements:
    - Database tables must exist (run reset_database.py first)
    - .env file with DATABASE_URL
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Password hashing configuration (same as application)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

# Load environment variables
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

# Add backend directory to Python path
sys.path.insert(0, str(backend_dir))

try:
    from app.core.database import get_session_local
    from app.core.database import User, Tenant, Organization, OrganizationMemberWhitelist
    from sqlalchemy import text
    logger.info("✅ Successfully imported database components")
except ImportError as e:
    logger.error(f"❌ Failed to import database components: {e}")
    sys.exit(1)

# ========================================
# PROFESSIONAL DATA CONFIGURATION
# ========================================

DATA_CONFIG = {
    # Super Admin Configuration
    "super_admin": {
        "email": "admin@defaultrate.com",
        "username": "super_admin",
        "password": "SuperAdmin123!",
        "full_name": "System Administrator",
        "role": "super_admin"
    },
    
    # Tenant Configuration
    "tenant": {
        "name": "FinTech Solutions Enterprise",
        "slug": "fintech-solutions",
        "domain": "fintech-solutions.com",
        "description": "Leading financial technology and risk assessment platform"
    },
    
    # Tenant Admin Configuration
    "tenant_admin": {
        "email": "admin@fintech-solutions.com",
        "username": "tenant_admin",
        "password": "TenantAdmin123!",
        "full_name": "Robert Johnson",
        "role": "tenant_admin"
    },
    
    # Organizations Configuration
    "organizations": [
        {
            "name": "Risk Assessment Division",
            "slug": "risk-assessment",
            "domain": "risk.fintech-solutions.com",
            "description": "Specialized team for credit risk analysis and default prediction modeling",
            "default_role": "org_member",
            
            # Organization Admin
            "admin": {
                "email": "risk.admin@fintech-solutions.com",
                "username": "risk_admin",
                "password": "RiskAdmin123!",
                "full_name": "Sarah Williams",
                "role": "org_admin"
            },
            
            # Organization Members
            "members": [
                {
                    "email": "analyst1@fintech-solutions.com",
                    "username": "risk_analyst_1",
                    "password": "Analyst123!",
                    "full_name": "Michael Chen",
                    "role": "org_member"
                },
                {
                    "email": "analyst2@fintech-solutions.com",
                    "username": "risk_analyst_2", 
                    "password": "Analyst123!",
                    "full_name": "Emily Davis",
                    "role": "org_member"
                }
            ]
        },
        {
            "name": "Credit Analytics Department",
            "slug": "credit-analytics",
            "domain": "credit.fintech-solutions.com",
            "description": "Advanced analytics team focused on credit scoring and financial modeling",
            "default_role": "org_member",
            
            # Organization Admin
            "admin": {
                "email": "credit.admin@fintech-solutions.com",
                "username": "credit_admin",
                "password": "CreditAdmin123!",
                "full_name": "David Thompson",
                "role": "org_admin"
            },
            
            # Organization Members
            "members": [
                {
                    "email": "modeler1@fintech-solutions.com",
                    "username": "credit_modeler_1",
                    "password": "Modeler123!",
                    "full_name": "Jessica Rodriguez",
                    "role": "org_member"
                },
                {
                    "email": "modeler2@fintech-solutions.com",
                    "username": "credit_modeler_2",
                    "password": "Modeler123!",
                    "full_name": "Alex Kumar",
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
        db.flush()  # Flush to get the ID
        
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
    
    print(f"\n🏢 TENANT: {tenant.name}")
    print(f"   🌐 Domain: {tenant.domain}")
    print(f"   📝 Description: {tenant.description}")
    
    print(f"\n👔 TENANT ADMIN:")
    print(f"   📧 Email: {tenant_admin.email}")
    print(f"   👤 Username: {tenant_admin.username}")
    print(f"   🔑 Password: {DATA_CONFIG['tenant_admin']['password']}")
    print(f"   🏷️  Role: {tenant_admin.role}")
    
    for i, org_data in enumerate(organizations_data, 1):
        org = org_data["organization"]
        admin = org_data["admin"]
        members = org_data["members"]
        
        print(f"\n🏛️  ORGANIZATION {i}: {org.name}")
        print(f"   🌐 Domain: {org.domain}")
        print(f"   🔗 Join Token: {org.join_token}")
        
        print(f"\n   👨‍💼 ORGANIZATION ADMIN:")
        print(f"      📧 Email: {admin.email}")
        print(f"      👤 Username: {admin.username}")
        print(f"      🔑 Password: {[org_conf for org_conf in DATA_CONFIG['organizations'] if org_conf['name'] == org.name][0]['admin']['password']}")
        
        print(f"\n   👥 ORGANIZATION MEMBERS:")
        for j, member in enumerate(members, 1):
            member_config = [org_conf for org_conf in DATA_CONFIG['organizations'] if org_conf['name'] == org.name][0]['members'][j-1]
            print(f"      {j}. {member.full_name}")
            print(f"         📧 Email: {member.email}")
            print(f"         👤 Username: {member.username}")
            print(f"         🔑 Password: {member_config['password']}")
    
    print("\n✅ NEXT STEPS:")
    print("1. 🚀 Start your FastAPI application server")
    print("2. 📬 Import the corrected Postman collection")
    print("3. 🔐 Use the login credentials above to test authentication")
    print("4. 🧪 Test the API endpoints with different user roles")
    
    print("\n📝 NOTES:")
    print("- All passwords follow strong security practices")
    print("- Email addresses use professional domain names")
    print("- Users are properly assigned to their respective organizations")
    print("- Whitelist entries created for all organization members")
    print("- Join tokens generated for organization access")

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
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("Please run 'python scripts/reset_database.py' first")
        sys.exit(1)
    
    # Setup data
    success = setup_application_data()
    
    if not success:
        logger.error("❌ Application data setup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
