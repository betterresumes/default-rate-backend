#!/usr/bin/env python3
"""
Check what data already exists in the database
"""

import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the app directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.database import User, Tenant, Organization, Company

# Database setup - using direct DATABASE_URL
DATABASE_URL = "postgresql://neondb_owner:npg_2ZLE4VuBytOa@ep-crimson-cell-adrxvu8a-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_existing_data():
    """Check what data currently exists in database"""
    session = SessionLocal()
    
    try:
        print("🔍 Checking existing data in database...")
        print("="*60)
        
        # Check Users
        users = session.query(User).all()
        print(f"\n👥 USERS ({len(users)}):")
        for user in users:
            print(f"   - {user.email} ({user.role}) - {user.full_name}")
            if user.tenant_id:
                tenant = session.query(Tenant).filter(Tenant.id == user.tenant_id).first()
                print(f"     Tenant: {tenant.name if tenant else 'Unknown'}")
            if user.organization_id:
                org = session.query(Organization).filter(Organization.id == user.organization_id).first()
                print(f"     Organization: {org.name if org else 'Unknown'}")
        
        # Check Tenants
        tenants = session.query(Tenant).all()
        print(f"\n🏢 TENANTS ({len(tenants)}):")
        for tenant in tenants:
            print(f"   - {tenant.name} (slug: {tenant.slug})")
        
        # Check Organizations
        organizations = session.query(Organization).all()
        print(f"\n🏛️ ORGANIZATIONS ({len(organizations)}):")
        for org in organizations:
            tenant = session.query(Tenant).filter(Tenant.id == org.tenant_id).first() if org.tenant_id else None
            print(f"   - {org.name} (slug: {org.slug})")
            print(f"     Tenant: {tenant.name if tenant else 'None'}")
            print(f"     Join Token: {org.join_token}")
        
        # Check Companies
        companies = session.query(Company).all()
        print(f"\n🏭 COMPANIES ({len(companies)}):")
        for company in companies:
            print(f"   - {company.symbol}: {company.name}")
        
        print("\n" + "="*60)
        print("✅ Database check completed!")
        
    except Exception as e:
        print(f"❌ Error checking database: {str(e)}")
        raise
    finally:
        session.close()

if __name__ == "__main__":
    check_existing_data()
