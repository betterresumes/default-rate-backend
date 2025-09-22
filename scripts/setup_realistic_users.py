#!/usr/bin/env python3
"""
Enhanced Professional Application Data Setup Script

This script creates realistic professional users with:
- 1 Super Admin
- 1 Tenant Admin  
- 2 Organizations with realistic business names
- Org admins and members with professional names and emails
- No test predictions or companies (users only)

Usage:
    python scripts/setup_realistic_users.py
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

# Password hashing configuration
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
# REALISTIC PROFESSIONAL DATA
# ========================================

DATA_CONFIG = {
    # Super Admin Configuration
    "super_admin": {
        "email": "admin@defaultrate.com",
        "username": "admin",
        "password": "Admin123!",
        "full_name": "John Smith",
        "role": "super_admin"
    },
    
    # Tenant Configuration
    "tenant": {
        "name": "Default Rate Analytics Inc.",
        "slug": "default-rate-analytics", 
        "domain": "defaultrate.com",
        "description": "Leading provider of credit risk assessment and default rate prediction services"
    },
    
    # Tenant Admin Configuration
    "tenant_admin": {
        "email": "ceo@defaultrate.com",
        "username": "ceo",
        "password": "CEO123!",
        "full_name": "Jennifer Thompson",
        "role": "tenant_admin"
    },
    
    # Organizations Configuration
    "organizations": [
        {
            "name": "Morgan Stanley Credit Risk Division",
            "slug": "morgan-stanley-credit",
            "domain": "credit.morganstanley.com", 
            "description": "Investment banking credit risk assessment and portfolio management team",
            "default_role": "org_member",
            
            # Organization Admin
            "admin": {
                "email": "risk.director@morganstanley.com",
                "username": "risk_director",
                "password": "Director123!",
                "full_name": "Robert Chen",
                "role": "org_admin"
            },
            
            # Organization Members
            "members": [
                {
                    "email": "sarah.williams@morganstanley.com",
                    "username": "sarah_williams",
                    "password": "Analyst123!",
                    "full_name": "Sarah Williams",
                    "role": "org_member"
                },
                {
                    "email": "michael.rodriguez@morganstanley.com",
                    "username": "michael_rodriguez",
                    "password": "Analyst123!",
                    "full_name": "Michael Rodriguez",
                    "role": "org_member"
                },
                {
                    "email": "lisa.anderson@morganstanley.com",
                    "username": "lisa_anderson", 
                    "password": "Analyst123!",
                    "full_name": "Lisa Anderson",
                    "role": "org_member"
                }
            ]
        },
        {
            "name": "JPMorgan Chase Risk Analytics",
            "slug": "jpmorgan-risk-analytics",
            "domain": "risk.jpmorgan.com",
            "description": "Commercial banking risk analytics and credit assessment division", 
            "default_role": "org_member",
            
            # Organization Admin
            "admin": {
                "email": "analytics.head@jpmorgan.com",
                "username": "analytics_head",
                "password": "Manager123!",
                "full_name": "David Kumar",
                "role": "org_admin"
            },
            
            # Organization Members
            "members": [
                {
                    "email": "emily.davis@jpmorgan.com",
                    "username": "emily_davis",
                    "password": "Analyst123!",
                    "full_name": "Emily Davis",
                    "role": "org_member"
                },
                {
                    "email": "james.wilson@jpmorgan.com",
                    "username": "james_wilson",
                    "password": "Analyst123!", 
                    "full_name": "James Wilson",
                    "role": "org_member"
                },
                {
                    "email": "maria.garcia@jpmorgan.com",
                    "username": "maria_garcia",
                    "password": "Analyst123!",
                    "full_name": "Maria Garcia", 
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

def setup_realistic_users():
    """Main function to set up all realistic user data"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        logger.info("🚀 Starting realistic user data setup...")
        
        # Create Super Admin
        logger.info("👑 Creating Super Admin...")
        admin_data = DATA_CONFIG["super_admin"]
        super_admin = create_user(db, admin_data)
        
        # Create Tenant
        logger.info("🏢 Creating Tenant...")
        tenant_data = DATA_CONFIG["tenant"]
        tenant = Tenant(
            name=tenant_data["name"],
            slug=tenant_data["slug"],
            domain=tenant_data["domain"],
            description=tenant_data["description"],
            is_active=True,
            created_by=super_admin.id,
            created_at=datetime.now()
        )
        db.add(tenant)
        db.flush()
        logger.info(f"✅ Tenant created: {tenant_data['name']}")
        
        # Create Tenant Admin
        logger.info("👔 Creating Tenant Admin...")
        tenant_admin_data = DATA_CONFIG["tenant_admin"]
        tenant_admin = create_user(db, tenant_admin_data, tenant_id=tenant.id)
        
        # Create Organizations with Users
        organizations_data = []
        for i, org_config in enumerate(DATA_CONFIG["organizations"], 1):
            logger.info(f"🏛️  Creating Organization {i}: {org_config['name']}")
            
            # Create organization
            organization = Organization(
                tenant_id=tenant.id,
                name=org_config["name"],
                slug=org_config["slug"],
                domain=org_config["domain"],
                description=org_config["description"],
                join_token=generate_join_token(),
                join_enabled=True,
                default_role=org_config["default_role"],
                max_users=500,
                is_active=True,
                created_by=tenant_admin.id,
                created_at=datetime.now()
            )
            db.add(organization)
            db.flush()
            logger.info(f"✅ Organization created: {org_config['name']}")
            
            # Create organization admin
            logger.info(f"👨‍💼 Creating Organization Admin...")
            admin_data = org_config["admin"]
            org_admin = create_user(db, admin_data, organization_id=organization.id)
            
            # Add admin to whitelist
            whitelist_entry = OrganizationMemberWhitelist(
                organization_id=organization.id,
                email=admin_data["email"],
                added_by=tenant_admin.id,
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
            
            organizations_data.append({
                "organization": organization,
                "admin": org_admin,
                "members": members
            })
            
            logger.info(f"✅ {org_config['name']} setup complete: {len(org_config['members'])} members created")
        
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
    """Print a comprehensive summary of created users"""
    logger.info("\n" + "=" * 70)
    logger.info("🎉 REALISTIC USER SETUP COMPLETED!")
    logger.info("=" * 70)
    
    total_users = 1 + 1 + sum(1 + len(org_data["members"]) for org_data in organizations_data)
    
    print(f"\n📋 SETUP SUMMARY:")
    print(f"📊 Total Users Created: {total_users}")
    print(f"🏢 Tenant Created: 1")
    print(f"🏛️  Organizations Created: {len(organizations_data)}")
    
    print(f"\n👑 SUPER ADMIN:")
    print(f"   👤 Name: {super_admin.full_name}")
    print(f"   📧 Email: {super_admin.email}")
    print(f"   🔑 Password: {DATA_CONFIG['super_admin']['password']}")
    print(f"   🏷️  Role: {super_admin.role}")
    
    print(f"\n🏢 TENANT: {tenant.name}")
    print(f"   🌐 Domain: {tenant.domain}")
    
    print(f"\n👔 TENANT ADMIN:")
    print(f"   👤 Name: {tenant_admin.full_name}")
    print(f"   📧 Email: {tenant_admin.email}")
    print(f"   🔑 Password: {DATA_CONFIG['tenant_admin']['password']}")
    print(f"   🏷️  Role: {tenant_admin.role}")
    
    for i, org_data in enumerate(organizations_data, 1):
        org = org_data["organization"]
        admin = org_data["admin"]
        members = org_data["members"]
        
        print(f"\n🏛️  ORGANIZATION {i}: {org.name}")
        print(f"   🌐 Domain: {org.domain}")
        
        print(f"\n   👨‍💼 ADMIN:")
        print(f"      👤 Name: {admin.full_name}")
        print(f"      📧 Email: {admin.email}")
        admin_config = [o for o in DATA_CONFIG['organizations'] if o['name'] == org.name][0]['admin']
        print(f"      🔑 Password: {admin_config['password']}")
        
        print(f"\n   👥 MEMBERS ({len(members)}):")
        for j, member in enumerate(members, 1):
            member_config = [o for o in DATA_CONFIG['organizations'] if o['name'] == org.name][0]['members'][j-1]
            print(f"      {j}. {member.full_name}")
            print(f"         📧 Email: {member.email}")
            print(f"         🔑 Password: {member_config['password']}")
    
    print(f"\n✅ NEXT STEPS:")
    print(f"1. 🚀 Start your FastAPI server")
    print(f"2. 🔐 Login with any of the above credentials")
    print(f"3. 📊 Test the /api/v1/predictions/stats endpoint with super admin")
    print(f"4. 📈 Create some predictions to see the stats in action")
    
    print(f"\n📝 NOTES:")
    print(f"- All users have professional names and realistic email addresses")
    print(f"- Organizations represent real financial institutions")
    print(f"- No test predictions or companies created - clean slate for testing")
    print(f"- Super admin can access the comprehensive statistics dashboard")

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🏗️  Default Rate System - Realistic User Setup")
    logger.info("=" * 60)
    
    # Verify database connection
    try:
        SessionLocal = get_session_local()
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Setup users
    success = setup_realistic_users()
    
    if not success:
        logger.error("❌ Realistic user setup failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
