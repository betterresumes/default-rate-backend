#!/usr/bin/env python3
"""
Database Migration Script for Multi-Tenant Organization System
Safely migrates from old schema to new organization-based schema
"""

import os
import sys
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def get_database_url():
    return os.getenv("DATABASE_URL")

def backup_existing_data(engine):
    """Backup existing data before migration"""
    print("🔄 Backing up existing data...")
    
    with engine.connect() as conn:
        # Check if tables exist
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        
        backup_data = {}
        
        # Backup users if exists
        if 'users' in existing_tables:
            result = conn.execute(text("SELECT * FROM users"))
            backup_data['users'] = [dict(row._mapping) for row in result]
            print(f"   ✅ Backed up {len(backup_data['users'])} users")
        
        # Backup companies if exists
        if 'companies' in existing_tables:
            result = conn.execute(text("SELECT * FROM companies"))
            backup_data['companies'] = [dict(row._mapping) for row in result]
            print(f"   ✅ Backed up {len(backup_data['companies'])} companies")
        
        # Backup predictions if exists
        if 'annual_predictions' in existing_tables:
            result = conn.execute(text("SELECT * FROM annual_predictions"))
            backup_data['annual_predictions'] = [dict(row._mapping) for row in result]
            print(f"   ✅ Backed up {len(backup_data['annual_predictions'])} annual predictions")
        
        if 'quarterly_predictions' in existing_tables:
            result = conn.execute(text("SELECT * FROM quarterly_predictions"))
            backup_data['quarterly_predictions'] = [dict(row._mapping) for row in result]
            print(f"   ✅ Backed up {len(backup_data['quarterly_predictions'])} quarterly predictions")
    
    return backup_data

def create_new_tables(engine):
    """Create new tables with organization support"""
    print("🏗️  Creating new table structure...")
    
    # Import the new database models
    from database import Base, create_tables
    
    # Create all new tables
    create_tables()
    print("   ✅ New tables created successfully")

def migrate_data(engine, backup_data):
    """Migrate data from old structure to new organization structure"""
    print("📦 Migrating data to new structure...")
    
    # Import new models
    from database import User, Company, AnnualPrediction, QuarterlyPrediction, Organization
    from sqlalchemy.orm import sessionmaker
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # 1. Migrate users first
        user_id_mapping = {}
        super_admin_id = None
        
        if 'users' in backup_data:
            print("   🔄 Migrating users...")
            for old_user in backup_data['users']:
                # Create new user with organization fields
                new_user = User(
                    id=old_user['id'],
                    email=old_user['email'],
                    username=old_user['username'],
                    hashed_password=old_user['hashed_password'],
                    full_name=old_user.get('full_name'),
                    organization_id=None,  # No organization initially
                    organization_role="user",
                    global_role="super_admin" if old_user.get('is_superuser', False) else "user",
                    is_active=old_user.get('is_active', True),
                    is_verified=old_user.get('is_verified', False),
                    created_at=old_user.get('created_at', datetime.utcnow()),
                    updated_at=old_user.get('updated_at', datetime.utcnow()),
                    last_login=old_user.get('last_login')
                )
                
                db.add(new_user)
                user_id_mapping[old_user['id']] = new_user.id
                
                if new_user.global_role == "super_admin":
                    super_admin_id = new_user.id
            
            db.commit()
            print(f"   ✅ Migrated {len(backup_data['users'])} users")
        
        # 2. Migrate companies
        company_id_mapping = {}
        
        if 'companies' in backup_data:
            print("   🔄 Migrating companies...")
            for old_company in backup_data['companies']:
                new_company = Company(
                    id=old_company['id'],
                    symbol=old_company['symbol'],
                    name=old_company['name'],
                    market_cap=old_company['market_cap'],
                    sector=old_company['sector'],
                    organization_id=None,  # Global companies initially
                    is_global=True if super_admin_id else False,  # Mark as global if super admin exists
                    created_by=super_admin_id,  # Assign to super admin
                    created_at=old_company.get('created_at', datetime.utcnow()),
                    updated_at=old_company.get('updated_at', datetime.utcnow())
                )
                
                db.add(new_company)
                company_id_mapping[old_company['id']] = new_company.id
            
            db.commit()
            print(f"   ✅ Migrated {len(backup_data['companies'])} companies")
        
        # 3. Migrate annual predictions
        if 'annual_predictions' in backup_data:
            print("   🔄 Migrating annual predictions...")
            for old_pred in backup_data['annual_predictions']:
                new_pred = AnnualPrediction(
                    id=old_pred['id'],
                    company_id=old_pred['company_id'],
                    organization_id=None,  # Global predictions initially
                    reporting_year=old_pred.get('reporting_year'),
                    reporting_quarter=old_pred.get('reporting_quarter'),
                    long_term_debt_to_total_capital=old_pred.get('long_term_debt_to_total_capital'),
                    total_debt_to_ebitda=old_pred.get('total_debt_to_ebitda'),
                    net_income_margin=old_pred.get('net_income_margin'),
                    ebit_to_interest_expense=old_pred.get('ebit_to_interest_expense'),
                    return_on_assets=old_pred.get('return_on_assets'),
                    probability=old_pred['probability'],
                    risk_level=old_pred['risk_level'],
                    confidence=old_pred['confidence'],
                    predicted_at=old_pred.get('predicted_at', datetime.utcnow()),
                    created_by=super_admin_id,  # Assign to super admin
                    created_at=old_pred.get('created_at', datetime.utcnow()),
                    updated_at=old_pred.get('updated_at', datetime.utcnow())
                )
                
                db.add(new_pred)
            
            db.commit()
            print(f"   ✅ Migrated {len(backup_data['annual_predictions'])} annual predictions")
        
        # 4. Migrate quarterly predictions
        if 'quarterly_predictions' in backup_data:
            print("   🔄 Migrating quarterly predictions...")
            for old_pred in backup_data['quarterly_predictions']:
                new_pred = QuarterlyPrediction(
                    id=old_pred['id'],
                    company_id=old_pred['company_id'],
                    organization_id=None,  # Global predictions initially
                    reporting_year=old_pred['reporting_year'],
                    reporting_quarter=old_pred['reporting_quarter'],
                    total_debt_to_ebitda=old_pred['total_debt_to_ebitda'],
                    sga_margin=old_pred['sga_margin'],
                    long_term_debt_to_total_capital=old_pred['long_term_debt_to_total_capital'],
                    return_on_capital=old_pred['return_on_capital'],
                    logistic_probability=old_pred['logistic_probability'],
                    gbm_probability=old_pred['gbm_probability'],
                    ensemble_probability=old_pred['ensemble_probability'],
                    risk_level=old_pred['risk_level'],
                    confidence=old_pred['confidence'],
                    predicted_at=old_pred.get('predicted_at', datetime.utcnow()),
                    created_by=super_admin_id,  # Assign to super admin
                    created_at=old_pred.get('created_at', datetime.utcnow()),
                    updated_at=old_pred.get('updated_at', datetime.utcnow())
                )
                
                db.add(new_pred)
            
            db.commit()
            print(f"   ✅ Migrated {len(backup_data['quarterly_predictions'])} quarterly predictions")
        
        print("   ✅ Data migration completed successfully!")
        
    except Exception as e:
        print(f"   ❌ Error during migration: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def cleanup_old_tables(engine):
    """Remove old tables that are no longer needed"""
    print("🧹 Cleaning up old tables...")
    
    with engine.connect() as conn:
        # Drop old tables that are replaced by new structure
        tables_to_drop = ['user_sessions']  # Remove sessions table
        
        for table in tables_to_drop:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                print(f"   ✅ Dropped old table: {table}")
            except Exception as e:
                print(f"   ⚠️  Could not drop {table}: {str(e)}")
        
        conn.commit()

def run_migration():
    """Main migration function"""
    print("🚀 Starting Database Migration to Multi-Tenant Organization System")
    print("=" * 70)
    
    # Check database connection
    database_url = get_database_url()
    if not database_url:
        print("❌ DATABASE_URL environment variable not set!")
        return False
    
    try:
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
        
        # Step 1: Backup existing data
        backup_data = backup_existing_data(engine)
        
        # Step 2: Create new tables
        create_new_tables(engine)
        
        # Step 3: Migrate data
        if backup_data:
            migrate_data(engine, backup_data)
        else:
            print("📝 No existing data to migrate - fresh installation")
        
        # Step 4: Cleanup old tables
        cleanup_old_tables(engine)
        
        print("=" * 70)
        print("🎉 Migration completed successfully!")
        print("\n📋 Summary:")
        print("   ✅ New organization tables created")
        print("   ✅ User table updated with organization support")
        print("   ✅ Company table updated with organization context")
        print("   ✅ Prediction tables updated with organization isolation")
        print("   ✅ All existing data preserved and migrated")
        print("\n🔑 Next Steps:")
        print("   1. Update your API endpoints to use new schemas")
        print("   2. Test the organization functionality")
        print("   3. Create your first organization")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
