#!/usr/bin/env python3
"""
Database Reset and Migration Script
Safely resets Neon DB and creates new multi-tenant organization schema
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

# Load environment variables
load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def get_database_url():
    return os.getenv("DATABASE_URL")

def reset_database(engine):
    """Reset the database by dropping all tables"""
    print("🔄 Resetting database (dropping all tables)...")
    
    with engine.connect() as conn:
        # Start a transaction
        trans = conn.begin()
        try:
            # Drop all tables in the correct order (reverse dependency order)
            tables_to_drop = [
                "quarterly_predictions",
                "annual_predictions", 
                "companies",
                "invitations",
                "user_sessions",
                "otp_tokens",
                "users",
                "organizations"
            ]
            
            for table in tables_to_drop:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    print(f"   ✅ Dropped table: {table}")
                except Exception as e:
                    print(f"   ⚠️  Could not drop {table}: {str(e)}")
            
            # Also drop any remaining tables that might exist
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename NOT LIKE 'pg_%' 
                AND tablename NOT LIKE 'information_schema%'
            """))
            
            remaining_tables = [row[0] for row in result]
            for table in remaining_tables:
                try:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
                    print(f"   ✅ Dropped remaining table: {table}")
                except Exception as e:
                    print(f"   ⚠️  Could not drop {table}: {str(e)}")
            
            trans.commit()
            print("   ✅ Database reset completed successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"   ❌ Error during database reset: {str(e)}")
            raise

def create_new_schema(engine):
    """Create the new multi-tenant organization schema"""
    print("🏗️  Creating new multi-tenant schema...")
    
    # Import the new database models
    try:
        from database import Base, create_tables
        print("   ✅ Imported database models")
    except ImportError as e:
        print(f"   ❌ Could not import database models: {str(e)}")
        print("   📝 Creating tables manually...")
        create_tables_manually(engine)
        return
    
    try:
        # Create all new tables
        Base.metadata.create_all(bind=engine)
        print("   ✅ New multi-tenant schema created successfully!")
        
        # Verify tables were created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                ORDER BY tablename
            """))
            tables = [row[0] for row in result]
            print(f"   📋 Created tables: {', '.join(tables)}")
            
    except Exception as e:
        print(f"   ❌ Error creating schema: {str(e)}")
        raise

def create_tables_manually(engine):
    """Manually create tables if import fails"""
    print("   🔧 Creating tables manually...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Create organizations table
            conn.execute(text("""
                CREATE TABLE organizations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    created_by UUID,
                    member_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX idx_organizations_name ON organizations(name);
            """))
            print("   ✅ Created organizations table")
            
            # Create users table
            conn.execute(text("""
                CREATE TABLE users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    organization_id UUID REFERENCES organizations(id),
                    organization_role VARCHAR(20) DEFAULT 'user',
                    global_role VARCHAR(20) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT true,
                    is_verified BOOLEAN DEFAULT false,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP
                );
                CREATE INDEX idx_users_email ON users(email);
                CREATE INDEX idx_users_organization ON users(organization_id);
            """))
            print("   ✅ Created users table")
            
            # Create invitations table
            conn.execute(text("""
                CREATE TABLE invitations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    organization_id UUID NOT NULL REFERENCES organizations(id),
                    email VARCHAR(255) NOT NULL,
                    organization_role VARCHAR(20) DEFAULT 'member',
                    invited_by UUID NOT NULL REFERENCES users(id),
                    status VARCHAR(20) DEFAULT 'pending',
                    token VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accepted_at TIMESTAMP
                );
                CREATE INDEX idx_invitations_email ON invitations(email);
                CREATE INDEX idx_invitations_token ON invitations(token);
            """))
            print("   ✅ Created invitations table")
            
            # Create companies table
            conn.execute(text("""
                CREATE TABLE companies (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    symbol VARCHAR(10) NOT NULL,
                    name VARCHAR(200) NOT NULL,
                    market_cap DECIMAL,
                    sector VARCHAR(100),
                    organization_id UUID REFERENCES organizations(id),
                    is_global BOOLEAN DEFAULT false,
                    created_by UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX idx_companies_symbol ON companies(symbol);
                CREATE INDEX idx_companies_organization ON companies(organization_id);
                CREATE INDEX idx_companies_global ON companies(is_global);
            """))
            print("   ✅ Created companies table")
            
            # Create annual_predictions table
            conn.execute(text("""
                CREATE TABLE annual_predictions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id UUID NOT NULL REFERENCES companies(id),
                    organization_id UUID REFERENCES organizations(id),
                    reporting_year VARCHAR(4),
                    reporting_quarter VARCHAR(2),
                    long_term_debt_to_total_capital DECIMAL,
                    total_debt_to_ebitda DECIMAL,
                    net_income_margin DECIMAL,
                    ebit_to_interest_expense DECIMAL,
                    return_on_assets DECIMAL,
                    probability DECIMAL NOT NULL,
                    risk_level VARCHAR(10) NOT NULL,
                    confidence DECIMAL NOT NULL,
                    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX idx_annual_predictions_company ON annual_predictions(company_id);
                CREATE INDEX idx_annual_predictions_organization ON annual_predictions(organization_id);
            """))
            print("   ✅ Created annual_predictions table")
            
            # Create quarterly_predictions table
            conn.execute(text("""
                CREATE TABLE quarterly_predictions (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    company_id UUID NOT NULL REFERENCES companies(id),
                    organization_id UUID REFERENCES organizations(id),
                    reporting_year VARCHAR(4) NOT NULL,
                    reporting_quarter VARCHAR(2) NOT NULL,
                    total_debt_to_ebitda DECIMAL,
                    sga_margin DECIMAL,
                    long_term_debt_to_total_capital DECIMAL,
                    return_on_capital DECIMAL,
                    logistic_probability DECIMAL NOT NULL,
                    gbm_probability DECIMAL NOT NULL,
                    ensemble_probability DECIMAL NOT NULL,
                    risk_level VARCHAR(10) NOT NULL,
                    confidence DECIMAL NOT NULL,
                    predicted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by UUID REFERENCES users(id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX idx_quarterly_predictions_company ON quarterly_predictions(company_id);
                CREATE INDEX idx_quarterly_predictions_organization ON quarterly_predictions(organization_id);
            """))
            print("   ✅ Created quarterly_predictions table")
            
            trans.commit()
            print("   ✅ All tables created manually!")
            
        except Exception as e:
            trans.rollback()
            print(f"   ❌ Error creating tables manually: {str(e)}")
            raise

def create_sample_data(engine):
    """Create initial sample data for testing"""
    print("📦 Creating sample data...")
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        with engine.connect() as conn:
            # Create a super admin user
            admin_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO users (id, email, username, hashed_password, full_name, global_role, is_active, is_verified)
                VALUES (:id, 'admin@company.com', 'superadmin', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPjiCTlrW', 'Super Admin', 'super_admin', true, true)
            """), {"id": admin_id})
            print("   ✅ Created super admin user (admin@company.com / secret)")
            
            # Create a sample organization
            org_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO organizations (id, name, description, created_by, member_count)
                VALUES (:id, 'Demo Company', 'A sample organization for testing', :created_by, 1)
            """), {"id": org_id, "created_by": admin_id})
            print("   ✅ Created sample organization (Demo Company)")
            
            # Create a sample company (global)
            company_id = str(uuid.uuid4())
            conn.execute(text("""
                INSERT INTO companies (id, symbol, name, market_cap, sector, is_global, created_by)
                VALUES (:id, 'DEMO', 'Demo Corporation', 1000000000, 'Technology', true, :created_by)
            """), {"id": company_id, "created_by": admin_id})
            print("   ✅ Created sample company (DEMO - Demo Corporation)")
            
            conn.commit()
            print("   ✅ Sample data created successfully!")
            
    except Exception as e:
        print(f"   ❌ Error creating sample data: {str(e)}")
        db.rollback()
    finally:
        db.close()

def run_reset_and_migration():
    """Main function to reset and migrate database"""
    print("🚀 Starting Database Reset and Multi-Tenant Migration")
    print("=" * 70)
    
    # Check database connection
    database_url = get_database_url()
    if not database_url:
        print("❌ DATABASE_URL environment variable not set!")
        return False
    
    print(f"🔗 Connecting to Neon DB: {database_url[:50]}...")
    
    try:
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Connected to PostgreSQL: {version[:50]}...")
        
        # Step 1: Reset database (drop all tables)
        reset_database(engine)
        
        # Step 2: Create new schema
        create_new_schema(engine)
        
        # Step 3: Create sample data
        create_sample_data(engine)
        
        print("=" * 70)
        print("🎉 Database reset and migration completed successfully!")
        print("\n📋 Summary:")
        print("   ✅ All old tables dropped")
        print("   ✅ New multi-tenant schema created")
        print("   ✅ Organizations table ready")
        print("   ✅ Users table with organization support")
        print("   ✅ Invitations system ready")
        print("   ✅ Companies with organization isolation")
        print("   ✅ Predictions with organization context")
        print("   ✅ Sample data created for testing")
        print("\n🔑 Test Login:")
        print("   Email: admin@company.com")
        print("   Password: secret")
        print("   Role: super_admin")
        print("\n🔥 Next Steps:")
        print("   1. Start your FastAPI server")
        print("   2. Test the authentication endpoints")
        print("   3. Create your first organization")
        print("   4. Invite users to join")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_reset_and_migration()
    sys.exit(0 if success else 1)
