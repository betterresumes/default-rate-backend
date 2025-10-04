#!/usr/bin/env python3
"""
Database Management Utility for Default Rate Prediction System

Usage:
    python scripts/db_admin.py [command] [options]

Commands:
    inspect     - Inspect database structure and data
    connect     - Get database connection information
    users       - List and manage users
    reset       - Reset database (danger!)
    backup      - Create database backup
    restore     - Restore from backup
"""

import os
import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

# Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)
sys.path.insert(0, str(backend_dir))

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://neondb_owner:npg_FRS5ptsg3QcE@ep-snowy-darkness-adw0r2ai-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=5)

try:
    from app.core.database import User, Tenant, Organization, OrganizationMemberWhitelist, Company, AnnualPrediction, QuarterlyPrediction, BulkUploadJob
except ImportError as e:
    logger.error(f"Failed to import database models: {e}")
    sys.exit(1)

def get_db_session():
    """Get database session"""
    engine = create_engine(DATABASE_URL, echo=False)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal(), engine

def inspect_database():
    """Inspect database structure and data"""
    db, engine = get_db_session()
    
    try:
        print("🔍 DATABASE INSPECTION")
        print("=" * 50)
        
        # Database info
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n📊 Database Overview:")
        print(f"   Host: {DATABASE_URL.split('@')[1].split('/')[0]}")
        print(f"   Database: {DATABASE_URL.split('/')[-1].split('?')[0]}")
        print(f"   Tables: {len(tables)}")
        
        # Table row counts
        print(f"\n📋 Table Row Counts:")
        table_models = {
            'users': User,
            'tenants': Tenant,
            'organizations': Organization,
            'organization_member_whitelists': OrganizationMemberWhitelist,
            'companies': Company,
            'annual_predictions': AnnualPrediction,
            'quarterly_predictions': QuarterlyPrediction,
            'bulk_upload_jobs': BulkUploadJob
        }
        
        for table_name, model in table_models.items():
            try:
                count = db.query(model).count()
                print(f"   {table_name}: {count:,}")
            except Exception as e:
                print(f"   {table_name}: Error ({str(e)[:50]}...)")
        
        # Recent activity
        print(f"\n⏰ Recent Activity (Last 24 hours):")
        try:
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(days=1)
            
            recent_users = db.query(User).filter(User.created_at >= yesterday).count()
            recent_predictions = db.query(AnnualPrediction).filter(AnnualPrediction.created_at >= yesterday).count()
            recent_jobs = db.query(BulkUploadJob).filter(BulkUploadJob.created_at >= yesterday).count()
            
            print(f"   New Users: {recent_users}")
            print(f"   New Predictions: {recent_predictions}")
            print(f"   New Jobs: {recent_jobs}")
        except Exception as e:
            print(f"   Unable to get recent activity: {e}")
        
    except Exception as e:
        logger.error(f"Inspection failed: {e}")
    finally:
        db.close()

def list_users(role_filter=None, limit=20):
    """List users with optional role filter"""
    db, engine = get_db_session()
    
    try:
        print(f"👥 USER LIST" + (f" (Role: {role_filter})" if role_filter else ""))
        print("=" * 80)
        
        query = db.query(User)
        if role_filter:
            query = query.filter(User.role == role_filter)
        
        users = query.order_by(User.created_at.desc()).limit(limit).all()
        
        if not users:
            print("No users found.")
            return
        
        print(f"{'ID':<8} {'Email':<30} {'Username':<20} {'Role':<15} {'Org':<20} {'Active':<8}")
        print("-" * 105)
        
        for user in users:
            org_name = user.organization.name[:18] + "..." if user.organization and len(user.organization.name) > 20 else (user.organization.name if user.organization else "None")
            active_status = "Yes" if user.is_active else "No"
            
            print(f"{str(user.id):<8} {user.email:<30} {user.username:<20} {user.role:<15} {org_name:<20} {active_status:<8}")
    
    except Exception as e:
        logger.error(f"Failed to list users: {e}")
    finally:
        db.close()

def create_super_admin_interactive():
    """Interactive super admin creation"""
    db, engine = get_db_session()
    
    try:
        print("👑 CREATE SUPER ADMIN")
        print("=" * 30)
        
        email = input("Email: ")
        username = input("Username: ")
        full_name = input("Full Name: ")
        password = input("Password (leave empty for default): ") or "SuperAdmin123!"
        
        # Check if user exists
        existing = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing:
            print(f"❌ User already exists: {existing.email}")
            return
        
        # Create user
        hashed_password = pwd_context.hash(password)
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            full_name=full_name,
            role="super_admin",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(user)
        db.commit()
        
        print(f"✅ Super Admin created successfully!")
        print(f"   ID: {user.id}")
        print(f"   Email: {user.email}")
        print(f"   Username: {user.username}")
        print(f"   Password: {password}")
        
    except Exception as e:
        logger.error(f"Failed to create super admin: {e}")
        db.rollback()
    finally:
        db.close()

def get_connection_info():
    """Display connection information"""
    print("🔗 DATABASE CONNECTION INFO")
    print("=" * 40)
    
    # Parse DATABASE_URL
    parts = DATABASE_URL.replace("postgresql://", "").split("@")
    credentials = parts[0]
    host_and_db = parts[1]
    
    username, password = credentials.split(":")
    host_port, db_params = host_and_db.split("/", 1)
    host = host_port.split(":")[0]
    port = host_port.split(":")[1] if ":" in host_port else "5432"
    database = db_params.split("?")[0]
    
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"Username: {username}")
    print(f"Password: {password}")
    print(f"\nFull URL: {DATABASE_URL}")
    
    print(f"\n🐘 PostgreSQL Client Commands:")
    print(f"   psql -h {host} -U {username} -d {database}")
    print(f"   PGPASSWORD='{password}' psql -h {host} -U {username} -d {database}")
    
    print(f"\n🔧 Environment Variable:")
    print(f"   export DATABASE_URL='{DATABASE_URL}'")

def reset_database_confirm():
    """Reset database with confirmation"""
    print("⚠️  DATABASE RESET WARNING")
    print("=" * 30)
    print("This will DELETE ALL DATA in the database!")
    print("This action CANNOT be undone!")
    
    confirm1 = input("\nType 'DELETE ALL DATA' to confirm: ")
    if confirm1 != "DELETE ALL DATA":
        print("Reset cancelled.")
        return
    
    confirm2 = input("Are you absolutely sure? (yes/no): ")
    if confirm2.lower() != "yes":
        print("Reset cancelled.")
        return
    
    db, engine = get_db_session()
    
    try:
        # Drop all tables
        from app.core.database import Base
        Base.metadata.drop_all(bind=engine)
        print("🗑️  All tables dropped")
        
        # Recreate tables
        Base.metadata.create_all(bind=engine)
        print("🏗️  All tables recreated")
        
        print("✅ Database reset complete")
        
    except Exception as e:
        logger.error(f"Reset failed: {e}")
    finally:
        db.close()

def export_data():
    """Export database data to JSON"""
    db, engine = get_db_session()
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"database_export_{timestamp}.json"
        
        print(f"📤 Exporting database to {filename}...")
        
        data = {
            "export_date": datetime.utcnow().isoformat(),
            "users": [],
            "tenants": [],
            "organizations": [],
            "companies": []
        }
        
        # Export users
        users = db.query(User).all()
        for user in users:
            data["users"].append({
                "id": str(user.id),
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "tenant_id": str(user.tenant_id) if user.tenant_id else None,
                "organization_id": str(user.organization_id) if user.organization_id else None,
                "created_at": user.created_at.isoformat() if user.created_at else None
            })
        
        # Export tenants
        tenants = db.query(Tenant).all()
        for tenant in tenants:
            data["tenants"].append({
                "id": str(tenant.id),
                "name": tenant.name,
                "slug": tenant.slug,
                "domain": tenant.domain,
                "description": tenant.description,
                "is_active": tenant.is_active,
                "created_at": tenant.created_at.isoformat() if tenant.created_at else None
            })
        
        # Export organizations
        orgs = db.query(Organization).all()
        for org in orgs:
            data["organizations"].append({
                "id": str(org.id),
                "tenant_id": str(org.tenant_id),
                "name": org.name,
                "slug": org.slug,
                "domain": org.domain,
                "description": org.description,
                "join_token": org.join_token,
                "max_users": org.max_users,
                "is_active": org.is_active,
                "created_at": org.created_at.isoformat() if org.created_at else None
            })
        
        # Export companies (limited)
        companies = db.query(Company).limit(1000).all()
        for company in companies:
            data["companies"].append({
                "id": str(company.id),
                "symbol": company.symbol,
                "name": company.name,
                "sector": company.sector,
                "market_cap": float(company.market_cap) if company.market_cap else None,
                "access_level": company.access_level
            })
        
        # Write to file
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✅ Export complete: {filename}")
        print(f"   Users: {len(data['users'])}")
        print(f"   Tenants: {len(data['tenants'])}")
        print(f"   Organizations: {len(data['organizations'])}")
        print(f"   Companies: {len(data['companies'])}")
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
    finally:
        db.close()

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description="Database Administration Tool")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Inspect command
    subparsers.add_parser('inspect', help='Inspect database structure and data')
    
    # Connect command
    subparsers.add_parser('connect', help='Show database connection information')
    
    # Users command
    users_parser = subparsers.add_parser('users', help='List and manage users')
    users_parser.add_argument('--role', help='Filter by role')
    users_parser.add_argument('--limit', type=int, default=20, help='Limit number of results')
    users_parser.add_argument('--create-admin', action='store_true', help='Create super admin interactively')
    
    # Reset command
    subparsers.add_parser('reset', help='Reset database (DANGER!)')
    
    # Export command
    subparsers.add_parser('export', help='Export database data to JSON')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    print("🛠️  Database Administration Tool")
    print("=" * 40)
    
    try:
        if args.command == 'inspect':
            inspect_database()
        elif args.command == 'connect':
            get_connection_info()
        elif args.command == 'users':
            if args.create_admin:
                create_super_admin_interactive()
            else:
                list_users(args.role, args.limit)
        elif args.command == 'reset':
            reset_database_confirm()
        elif args.command == 'export':
            export_data()
        else:
            print(f"Unknown command: {args.command}")
    
    except Exception as e:
        logger.error(f"Command failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
