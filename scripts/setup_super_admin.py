#!/usr/bin/env python3
"""
Enhanced Super Admin and Complete Tenant Setup Script

Usage:
    python scripts/setup_super_admin.py [--tenant-config CONFIG_NAME]

Features:
- Create super admin with full system access
- Set up complete tenant with organizations
- Flexible configuration system
- Database inspection tools
- User management utilities
"""

import os
import sys
import logging
import secrets
import string
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from passlib.context import CryptContext
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

# Paths
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

sys.path.insert(0, str(backend_dir))

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_FRS5ptsg3QcE@ep-snowy-darkness-adw0r2ai-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")

def get_session_local():
    """Create database session"""
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal, engine

# Import database models
try:
    from app.core.database import User, Tenant, Organization, OrganizationMemberWhitelist, Company
    logger.info("✅ Successfully imported database components")
except ImportError as e:
    logger.error(f"❌ Failed to import database components: {e}")
    sys.exit(1)

# Configuration templates
TENANT_CONFIGS = {
    "hdfc_bank": {
        "super_admin": {
            "email": "admin@defaultrate.com",
            "username": "super_admin_hdfc",
            "password": "SuperAdmin123!",
            "full_name": "System Administrator",
            "role": "super_admin"
        },
        "tenant": {
            "name": "HDFC Bank Limited",
            "slug": "hdfc-bank",
            "domain": "hdfcbank.com",
            "description": "India's leading private sector bank with advanced credit risk management"
        },
        "tenant_admin": {
            "email": "admin@hdfcbank.com",
            "username": "hdfc_admin",
            "password": "HdfcAdmin123!",
            "full_name": "HDFC Bank Administrator",
            "role": "tenant_admin"
        },
        "organizations": [
            {
                "name": "Credit Risk Management Division",
                "slug": "credit-risk-mgmt",
                "domain": "risk.hdfcbank.com",
                "description": "Advanced credit risk assessment and default prediction analytics",
                "max_users": 100,
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
                        "username": "senior_analyst",
                        "password": "Analyst123!",
                        "full_name": "Sneha Raghavan Nair",
                        "role": "org_member"
                    },
                    {
                        "email": "quant.analyst@hdfcbank.com",
                        "username": "quant_analyst",
                        "password": "Quant123!",
                        "full_name": "Arjun Vikram Singh",
                        "role": "org_member"
                    }
                ]
            },
            {
                "name": "Data Analytics & Machine Learning",
                "slug": "data-analytics",
                "domain": "analytics.hdfcbank.com",
                "description": "ML models and statistical analysis for financial risk prediction",
                "max_users": 75,
                "admin": {
                    "email": "analytics.head@hdfcbank.com",
                    "username": "analytics_head",
                    "password": "Analytics123!",
                    "full_name": "Dr. Kavitha Subramanian",
                    "role": "org_admin"
                },
                "members": [
                    {
                        "email": "data.scientist@hdfcbank.com",
                        "username": "data_scientist",
                        "password": "DataSci123!",
                        "full_name": "Rohit Agarwal Joshi",
                        "role": "org_member"
                    },
                    {
                        "email": "ml.engineer@hdfcbank.com",
                        "username": "ml_engineer",
                        "password": "MLEng123!",
                        "full_name": "Ananya Sharma Reddy",
                        "role": "org_member"
                    }
                ]
            }
        ]
    },
    
    "icici_bank": {
        "super_admin": {
            "email": "admin@defaultrate.com",
            "username": "super_admin_icici",
            "password": "SuperAdmin123!",
            "full_name": "System Administrator",
            "role": "super_admin"
        },
        "tenant": {
            "name": "ICICI Bank Limited",
            "slug": "icici-bank",
            "domain": "icicibank.com",
            "description": "India's largest private sector bank by consolidated assets"
        },
        "tenant_admin": {
            "email": "admin@icicibank.com",
            "username": "icici_admin",
            "password": "IciciAdmin123!",
            "full_name": "ICICI Bank Administrator",
            "role": "tenant_admin"
        },
        "organizations": [
            {
                "name": "Corporate Credit & Risk Assessment",
                "slug": "corporate-credit",
                "domain": "corporate.icicibank.com",
                "description": "Corporate lending and credit risk evaluation",
                "max_users": 150,
                "admin": {
                    "email": "corporate.head@icicibank.com",
                    "username": "corporate_head",
                    "password": "Corporate123!",
                    "full_name": "Dr. Ramesh Chandra Verma",
                    "role": "org_admin"
                },
                "members": [
                    {
                        "email": "credit.manager@icicibank.com",
                        "username": "credit_manager",
                        "password": "Credit123!",
                        "full_name": "Meera Krishnan Iyer",
                        "role": "org_member"
                    }
                ]
            }
        ]
    }
}

def generate_join_token():
    """Generate a secure join token"""
    return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

def inspect_database(engine):
    """Inspect database structure and existing data"""
    logger.info("🔍 Inspecting database structure...")
    
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    logger.info(f"📋 Found {len(tables)} tables: {', '.join(tables)}")
    
    # Check existing users
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        existing_users = db.query(User).count()
        existing_tenants = db.query(Tenant).count()
        existing_orgs = db.query(Organization).count()
        
        logger.info(f"👥 Existing users: {existing_users}")
        logger.info(f"🏢 Existing tenants: {existing_tenants}")
        logger.info(f"🏛️  Existing organizations: {existing_orgs}")
        
        if existing_users > 0:
            logger.warning("⚠️  Database already contains users. Use --force to proceed anyway.")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"❌ Database inspection failed: {e}")
        return False
    finally:
        db.close()

def create_user(db, user_data, tenant_id=None, organization_id=None):
    """Create a user with the specified data"""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == user_data["email"]) | 
            (User.username == user_data["username"])
        ).first()
        
        if existing_user:
            logger.warning(f"⚠️  User already exists: {user_data['email']}")
            return existing_user
        
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
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        db.flush()
        
        logger.info(f"✅ Created user: {user_data['full_name']} ({user_data['email']})")
        return user
        
    except Exception as e:
        logger.error(f"❌ Failed to create user {user_data['email']}: {e}")
        raise

def setup_complete_tenant(config_name="hdfc_bank", force=False):
    """Set up complete tenant with super admin"""
    SessionLocal, engine = get_session_local()
    
    # Inspect database first
    if not force and not inspect_database(engine):
        if not input("Continue anyway? (y/N): ").lower().startswith('y'):
            logger.info("Setup cancelled by user")
            return False
    
    db = SessionLocal()
    config = TENANT_CONFIGS[config_name]
    
    try:
        logger.info(f"🚀 Setting up complete tenant: {config['tenant']['name']}")
        
        # 1. Create Super Admin
        logger.info("👑 Creating Super Admin...")
        super_admin = create_user(db, config["super_admin"])
        
        # 2. Create Tenant
        logger.info("🏢 Creating Tenant...")
        tenant_data = config["tenant"]
        
        existing_tenant = db.query(Tenant).filter(
            (Tenant.slug == tenant_data["slug"]) | 
            (Tenant.domain == tenant_data["domain"])
        ).first()
        
        if existing_tenant:
            logger.warning(f"⚠️  Tenant already exists: {tenant_data['name']}")
            tenant = existing_tenant
        else:
            tenant = Tenant(
                name=tenant_data["name"],
                slug=tenant_data["slug"],
                domain=tenant_data["domain"],
                description=tenant_data["description"],
                is_active=True,
                created_by=super_admin.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(tenant)
            db.flush()
            logger.info(f"✅ Created tenant: {tenant_data['name']}")
        
        # 3. Create Tenant Admin
        logger.info("👔 Creating Tenant Admin...")
        tenant_admin = create_user(db, config["tenant_admin"], tenant_id=tenant.id)
        
        # 4. Create Organizations
        organizations_data = []
        for org_config in config["organizations"]:
            logger.info(f"🏛️  Creating Organization: {org_config['name']}")
            
            # Create organization
            existing_org = db.query(Organization).filter(
                Organization.slug == org_config["slug"]
            ).first()
            
            if existing_org:
                logger.warning(f"⚠️  Organization already exists: {org_config['name']}")
                organization = existing_org
            else:
                organization = Organization(
                    tenant_id=tenant.id,
                    name=org_config["name"],
                    slug=org_config["slug"],
                    domain=org_config["domain"],
                    description=org_config["description"],
                    join_token=generate_join_token(),
                    join_enabled=True,
                    default_role="org_member",
                    max_users=org_config.get("max_users", 500),
                    is_active=True,
                    allow_global_data_access=False,
                    created_by=tenant_admin.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                db.add(organization)
                db.flush()
                logger.info(f"✅ Created organization: {org_config['name']}")
            
            # Create organization admin
            org_admin = create_user(db, org_config["admin"], organization_id=organization.id)
            
            # Add admin to whitelist
            whitelist_admin = OrganizationMemberWhitelist(
                organization_id=organization.id,
                email=org_config["admin"]["email"],
                added_by=tenant_admin.id,
                added_at=datetime.utcnow(),
                status="active"
            )
            db.add(whitelist_admin)
            
            # Create organization members
            members = []
            for member_data in org_config["members"]:
                member = create_user(db, member_data, organization_id=organization.id)
                members.append(member)
                
                # Add member to whitelist
                whitelist_member = OrganizationMemberWhitelist(
                    organization_id=organization.id,
                    email=member_data["email"],
                    added_by=org_admin.id,
                    added_at=datetime.utcnow(),
                    status="active"
                )
                db.add(whitelist_member)
            
            organizations_data.append({
                "organization": organization,
                "admin": org_admin,
                "members": members
            })
        
        # Commit all changes
        db.commit()
        logger.info("💾 All data committed successfully!")
        
        # Print summary
        print_setup_summary(super_admin, tenant, tenant_admin, organizations_data, config)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        db.rollback()
        raise
        
    finally:
        db.close()

def print_setup_summary(super_admin, tenant, tenant_admin, organizations_data, config):
    """Print comprehensive setup summary"""
    print("\n" + "=" * 80)
    print("🎉 COMPLETE TENANT SETUP SUCCESSFUL!")
    print("=" * 80)
    
    total_users = 1 + 1 + sum(1 + len(org["members"]) for org in organizations_data)
    
    print(f"\n📊 SETUP SUMMARY:")
    print(f"   👥 Total Users Created: {total_users}")
    print(f"   🏢 Tenants: 1")
    print(f"   🏛️  Organizations: {len(organizations_data)}")
    
    print(f"\n👑 SUPER ADMIN ACCESS:")
    print(f"   📧 Email: {super_admin.email}")
    print(f"   👤 Username: {super_admin.username}")
    print(f"   🔑 Password: {config['super_admin']['password']}")
    print(f"   🆔 User ID: {super_admin.id}")
    print(f"   🏷️  Role: {super_admin.role}")
    
    print(f"\n🏢 TENANT: {tenant.name}")
    print(f"   🆔 Tenant ID: {tenant.id}")
    print(f"   🌐 Domain: {tenant.domain}")
    print(f"   📝 Slug: {tenant.slug}")
    
    print(f"\n👔 TENANT ADMIN:")
    print(f"   📧 Email: {tenant_admin.email}")
    print(f"   👤 Username: {tenant_admin.username}")
    print(f"   🔑 Password: {config['tenant_admin']['password']}")
    print(f"   🆔 User ID: {tenant_admin.id}")
    
    for i, org_data in enumerate(organizations_data, 1):
        org = org_data["organization"]
        admin = org_data["admin"]
        members = org_data["members"]
        org_config = config["organizations"][i-1]
        
        print(f"\n🏛️  ORGANIZATION {i}: {org.name}")
        print(f"   🆔 Org ID: {org.id}")
        print(f"   🌐 Domain: {org.domain}")
        print(f"   🔗 Join Token: {org.join_token}")
        print(f"   👥 Max Users: {org.max_users}")
        
        print(f"\n   👨‍💼 ORG ADMIN:")
        print(f"      📧 Email: {admin.email}")
        print(f"      👤 Username: {admin.username}")
        print(f"      🔑 Password: {org_config['admin']['password']}")
        print(f"      🆔 User ID: {admin.id}")
        
        print(f"\n   👥 ORG MEMBERS ({len(members)}):")
        for j, member in enumerate(members):
            member_config = org_config["members"][j]
            print(f"      {j+1}. {member.full_name}")
            print(f"         📧 {member.email}")
            print(f"         👤 {member.username}")
            print(f"         🔑 {member_config['password']}")
            print(f"         🆔 {member.id}")
    
    print(f"\n🔗 DATABASE ACCESS:")
    print(f"   Database: neondb")
    print(f"   Host: ep-snowy-darkness-adw0r2ai-pooler.c-2.us-east-1.aws.neon.tech")
    print(f"   User: neondb_owner")
    
    print(f"\n🚀 NEXT STEPS:")
    print(f"   1. Use Super Admin credentials to access the system")
    print(f"   2. Super Admin can create/modify any tenant, organization, or user")
    print(f"   3. Tenant Admin can manage organizations within their tenant")
    print(f"   4. Org Admins can manage users within their organizations")
    print(f"   5. Use join tokens to allow users to self-register to organizations")

def list_existing_data():
    """List existing data in the database"""
    SessionLocal, engine = get_session_local()
    db = SessionLocal()
    
    try:
        print("\n🔍 EXISTING DATABASE DATA:")
        print("=" * 50)
        
        # Users
        users = db.query(User).all()
        print(f"\n👥 USERS ({len(users)}):")
        for user in users:
            org_name = user.organization.name if user.organization else "No Organization"
            tenant_name = user.tenant.name if user.tenant else "No Tenant"
            print(f"   • {user.full_name} ({user.email}) - {user.role}")
            print(f"     Tenant: {tenant_name}, Org: {org_name}")
        
        # Tenants
        tenants = db.query(Tenant).all()
        print(f"\n🏢 TENANTS ({len(tenants)}):")
        for tenant in tenants:
            org_count = len(tenant.organizations) if tenant.organizations else 0
            print(f"   • {tenant.name} ({tenant.domain}) - {org_count} orgs")
        
        # Organizations
        orgs = db.query(Organization).all()
        print(f"\n🏛️  ORGANIZATIONS ({len(orgs)}):")
        for org in orgs:
            member_count = db.query(User).filter(User.organization_id == org.id).count()
            tenant_name = org.tenant.name if org.tenant else "No Tenant"
            print(f"   • {org.name} ({org.domain}) - {member_count} members")
            print(f"     Tenant: {tenant_name}, Join Token: {org.join_token}")
        
    except Exception as e:
        logger.error(f"❌ Failed to list data: {e}")
    finally:
        db.close()

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Setup Super Admin and Complete Tenant")
    parser.add_argument("--config", choices=list(TENANT_CONFIGS.keys()), 
                       default="hdfc_bank", help="Tenant configuration to use")
    parser.add_argument("--force", action="store_true", 
                       help="Force setup even if data already exists")
    parser.add_argument("--list", action="store_true", 
                       help="List existing database data")
    
    args = parser.parse_args()
    
    logger.info("=" * 70)
    logger.info("🏗️  Default Rate Prediction System - Super Admin Setup")
    logger.info("=" * 70)
    
    # Test database connection
    try:
        SessionLocal, engine = get_session_local()
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    if args.list:
        list_existing_data()
        return
    
    # Setup tenant
    try:
        success = setup_complete_tenant(args.config, args.force)
        if success:
            logger.info("🎉 Setup completed successfully!")
        else:
            logger.error("❌ Setup failed")
            sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Setup failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
