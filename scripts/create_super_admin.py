#!/usr/bin/env python3
"""
Super Admin Setup and Complete Tenant Management System

This script creates a super admin user and provides a complete system to:
1. Create tenants
2. Set up organizations 
3. Create users
4. Manage the entire multi-tenant structure

Usage:
    python scripts/create_super_admin.py
"""

import os
import sys
import uuid
import secrets
import string
from datetime import datetime, timedelta
from pathlib import Path
from getpass import getpass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

# Import required modules
try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import sessionmaker
    from passlib.context import CryptContext
    
    from app.core.database import User, Tenant, Organization, OrganizationMemberWhitelist, Company
    from app.core.database import Base
    
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Please install: pip install sqlalchemy passlib[bcrypt] psycopg2-binary python-dotenv")
    sys.exit(1)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment variables")
    sys.exit(1)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=8)

# Database connection
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

def generate_secure_password(length=12):
    """Generate a secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_join_token():
    """Generate a secure join token"""
    return secrets.token_urlsafe(32)

def create_super_admin():
    """Create super admin user interactively"""
    print("👑 SUPER ADMIN CREATION")
    print("=" * 40)
    
    db = get_db()
    
    try:
        # Get admin details
        print("Enter super admin details:")
        email = input("Email: ").strip().lower()
        username = input("Username: ").strip()
        full_name = input("Full Name: ").strip()
        
        # Password options
        use_generated = input("Use auto-generated secure password? (y/n): ").strip().lower() == 'y'
        if use_generated:
            password = generate_secure_password(16)
            print(f"🔐 Generated password: {password}")
            input("Press Enter after noting down the password...")
        else:
            password = getpass("Password: ")
            if len(password) < 8:
                print("❌ Password must be at least 8 characters")
                return False
        
        # Check if user already exists
        existing = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing:
            print(f"❌ User already exists: {existing.email}")
            return False
        
        # Create super admin
        hashed_password = pwd_context.hash(password)
        super_admin = User(
            id=uuid.uuid4(),
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            role="super_admin",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            tenant_id=None,  # Super admin doesn't belong to any tenant
            organization_id=None
        )
        
        db.add(super_admin)
        db.commit()
        
        print("✅ Super Admin created successfully!")
        print(f"   ID: {super_admin.id}")
        print(f"   Email: {super_admin.email}")
        print(f"   Username: {super_admin.username}")
        print(f"   Role: {super_admin.role}")
        
        return super_admin
        
    except Exception as e:
        print(f"❌ Error creating super admin: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_complete_tenant_setup():
    """Create a complete tenant setup with organization and users"""
    print("\n🏢 COMPLETE TENANT SETUP")
    print("=" * 40)
    
    db = get_db()
    
    try:
        # Tenant details
        print("Enter tenant details:")
        tenant_name = input("Tenant Name: ").strip()
        tenant_slug = input("Tenant Slug (URL-friendly): ").strip().lower()
        tenant_domain = input("Tenant Domain (optional): ").strip() or None
        tenant_description = input("Description (optional): ").strip() or f"Tenant for {tenant_name}"
        
        # Check if tenant exists
        existing_tenant = db.query(Tenant).filter(
            (Tenant.name == tenant_name) | (Tenant.slug == tenant_slug)
        ).first()
        
        if existing_tenant:
            print(f"❌ Tenant already exists: {existing_tenant.name}")
            return False
        
        # Create tenant
        tenant = Tenant(
            id=uuid.uuid4(),
            name=tenant_name,
            slug=tenant_slug,
            domain=tenant_domain,
            description=tenant_description,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(tenant)
        db.flush()  # Get the ID
        
        print(f"✅ Tenant created: {tenant.name}")
        
        # Organization details
        print("\nEnter organization details:")
        org_name = input("Organization Name: ").strip()
        org_slug = input("Organization Slug: ").strip().lower()
        org_domain = input("Organization Domain (optional): ").strip() or None
        org_description = input("Description (optional): ").strip() or f"Organization for {org_name}"
        max_users = int(input("Max Users (default 100): ").strip() or "100")
        
        # Create organization
        join_token = generate_join_token()
        organization = Organization(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            name=org_name,
            slug=org_slug,
            domain=org_domain,
            description=org_description,
            join_token=join_token,
            max_users=max_users,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(organization)
        db.flush()
        
        print(f"✅ Organization created: {organization.name}")
        print(f"   Join Token: {join_token}")
        
        # Create tenant admin
        print("\nCreate tenant admin user:")
        admin_email = input("Admin Email: ").strip().lower()
        admin_username = input("Admin Username: ").strip()
        admin_full_name = input("Admin Full Name: ").strip()
        
        # Generate or ask for password
        use_generated_admin = input("Use auto-generated password for admin? (y/n): ").strip().lower() == 'y'
        if use_generated_admin:
            admin_password = generate_secure_password(12)
            print(f"🔐 Admin password: {admin_password}")
        else:
            admin_password = getpass("Admin Password: ")
        
        # Create admin user
        hashed_admin_password = pwd_context.hash(admin_password)
        admin_user = User(
            id=uuid.uuid4(),
            email=admin_email,
            username=admin_username,
            hashed_password=hashed_admin_password,
            full_name=admin_full_name,
            role="tenant_admin",
            is_active=True,
            tenant_id=tenant.id,
            organization_id=organization.id,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(admin_user)
        
        # Add admin to whitelist
        whitelist_entry = OrganizationMemberWhitelist(
            id=uuid.uuid4(),
            organization_id=organization.id,
            email=admin_email,
            role="tenant_admin",
            invited_by_user_id=None,  # System created
            created_at=datetime.utcnow()
        )
        
        db.add(whitelist_entry)
        
        # Create a few sample regular users
        create_samples = input("\nCreate sample users? (y/n): ").strip().lower() == 'y'
        sample_users = []
        
        if create_samples:
            sample_count = int(input("How many sample users? (default 3): ").strip() or "3")
            
            for i in range(sample_count):
                sample_email = f"user{i+1}@{tenant_slug}.com"
                sample_username = f"user{i+1}_{tenant_slug}"
                sample_password = generate_secure_password(10)
                
                sample_user = User(
                    id=uuid.uuid4(),
                    email=sample_email,
                    username=sample_username,
                    hashed_password=pwd_context.hash(sample_password),
                    full_name=f"Sample User {i+1}",
                    role="user",
                    is_active=True,
                    tenant_id=tenant.id,
                    organization_id=organization.id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                db.add(sample_user)
                sample_users.append({
                    'email': sample_email,
                    'username': sample_username,
                    'password': sample_password
                })
                
                # Add to whitelist
                sample_whitelist = OrganizationMemberWhitelist(
                    id=uuid.uuid4(),
                    organization_id=organization.id,
                    email=sample_email,
                    role="user",
                    invited_by_user_id=admin_user.id,
                    created_at=datetime.utcnow()
                )
                
                db.add(sample_whitelist)
        
        # Commit all changes
        db.commit()
        
        # Success summary
        print("\n🎉 COMPLETE TENANT SETUP SUCCESSFUL!")
        print("=" * 50)
        print(f"Tenant: {tenant.name} ({tenant.slug})")
        print(f"Organization: {organization.name}")
        print(f"Join Token: {join_token}")
        print(f"Admin: {admin_user.email} / {admin_user.username}")
        
        if sample_users:
            print(f"\nSample Users Created:")
            for user in sample_users:
                print(f"   {user['email']} / {user['username']} / {user['password']}")
        
        # Generate summary file
        summary_file = f"tenant_setup_{tenant_slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(summary_file, 'w') as f:
            f.write(f"Tenant Setup Summary\n")
            f.write(f"==================\n\n")
            f.write(f"Tenant: {tenant.name}\n")
            f.write(f"Slug: {tenant.slug}\n")
            f.write(f"Domain: {tenant.domain or 'None'}\n")
            f.write(f"Description: {tenant.description}\n\n")
            f.write(f"Organization: {organization.name}\n")
            f.write(f"Join Token: {join_token}\n")
            f.write(f"Max Users: {max_users}\n\n")
            f.write(f"Admin User:\n")
            f.write(f"  Email: {admin_user.email}\n")
            f.write(f"  Username: {admin_user.username}\n")
            f.write(f"  Password: {admin_password}\n\n")
            
            if sample_users:
                f.write(f"Sample Users:\n")
                for user in sample_users:
                    f.write(f"  {user['email']} / {user['username']} / {user['password']}\n")
        
        print(f"\n📄 Setup details saved to: {summary_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tenant setup: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def list_existing_data():
    """List existing tenants, organizations, and users"""
    print("\n📋 EXISTING DATA OVERVIEW")
    print("=" * 40)
    
    db = get_db()
    
    try:
        # Count everything
        tenant_count = db.query(Tenant).count()
        org_count = db.query(Organization).count()
        user_count = db.query(User).count()
        company_count = db.query(Company).count()
        
        print(f"📊 Database Overview:")
        print(f"   Tenants: {tenant_count}")
        print(f"   Organizations: {org_count}")
        print(f"   Users: {user_count}")
        print(f"   Companies: {company_count}")
        
        # List tenants
        if tenant_count > 0:
            print(f"\n🏢 Existing Tenants:")
            tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).limit(10).all()
            for tenant in tenants:
                org_count_for_tenant = db.query(Organization).filter(Organization.tenant_id == tenant.id).count()
                user_count_for_tenant = db.query(User).filter(User.tenant_id == tenant.id).count()
                status = "🟢" if tenant.is_active else "🔴"
                print(f"   {status} {tenant.name} ({tenant.slug}) - {org_count_for_tenant} orgs, {user_count_for_tenant} users")
        
        # List super admins
        super_admins = db.query(User).filter(User.role == "super_admin").all()
        if super_admins:
            print(f"\n👑 Super Admins:")
            for admin in super_admins:
                status = "🟢" if admin.is_active else "🔴"
                print(f"   {status} {admin.email} ({admin.username}) - {admin.full_name}")
        else:
            print(f"\n⚠️ No super admins found!")
        
    except Exception as e:
        print(f"❌ Error listing data: {e}")
    finally:
        db.close()

def main():
    """Main interactive menu"""
    print("🚀 SUPER ADMIN & TENANT MANAGEMENT SYSTEM")
    print("=" * 50)
    
    # Test database connection
    try:
        db = get_db()
        db.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        db.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Please check your DATABASE_URL and database status")
        return
    
    while True:
        print("\n🎯 What would you like to do?")
        print("1. Create Super Admin")
        print("2. Create Complete Tenant Setup")
        print("3. List Existing Data")
        print("4. Exit")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            create_super_admin()
        elif choice == '2':
            create_complete_tenant_setup()
        elif choice == '3':
            list_existing_data()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
