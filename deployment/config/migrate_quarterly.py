#!/usr/bin/env python3
"""
Database migration script to add quarterly prediction support
Adds new fields to the companies table for quarterly ML models
"""

import os
import sys
from sqlalchemy import create_engine, text

def get_database_url():
    """Get database URL from environment"""
    return os.getenv("DATABASE_URL")

def migrate_database():
    """Add new fields for quarterly predictions"""
    
    database_url = get_database_url()
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return False
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            print("🔄 Starting database migration for quarterly predictions...")
            
            # Start transaction
            trans = conn.begin()
            
            try:
                # 1. Add prediction_type column
                print("  ➡️  Adding prediction_type column...")
                conn.execute(text("""
                    ALTER TABLE companies 
                    ADD COLUMN IF NOT EXISTS prediction_type VARCHAR DEFAULT 'annual';
                """))
                
                # 2. Add quarterly-specific columns
                print("  ➡️  Adding quarterly model columns...")
                conn.execute(text("""
                    ALTER TABLE companies 
                    ADD COLUMN IF NOT EXISTS sga_margin NUMERIC(10,4),
                    ADD COLUMN IF NOT EXISTS return_on_capital NUMERIC(10,4),
                    ADD COLUMN IF NOT EXISTS logistic_probability NUMERIC(5,4),
                    ADD COLUMN IF NOT EXISTS gbm_probability NUMERIC(5,4);
                """))
                
                # 3. Make existing fields nullable for quarterly predictions
                print("  ➡️  Making annual fields nullable...")
                conn.execute(text("""
                    ALTER TABLE companies 
                    ALTER COLUMN long_term_debt_to_total_capital DROP NOT NULL,
                    ALTER COLUMN total_debt_to_ebitda DROP NOT NULL,
                    ALTER COLUMN net_income_margin DROP NOT NULL,
                    ALTER COLUMN ebit_to_interest_expense DROP NOT NULL,
                    ALTER COLUMN return_on_assets DROP NOT NULL;
                """))
                
                # 4. Remove unique constraint on symbol and add composite constraint
                print("  ➡️  Updating constraints...")
                try:
                    # Drop existing unique constraint if it exists
                    conn.execute(text("""
                        ALTER TABLE companies DROP CONSTRAINT IF EXISTS companies_symbol_key;
                    """))
                except:
                    pass  # Constraint might not exist
                
                # Add new composite unique constraint
                conn.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS idx_company_unique 
                    ON companies (symbol, prediction_type, reporting_year, reporting_quarter);
                """))
                
                # 5. Update existing records to have prediction_type = 'annual'
                print("  ➡️  Updating existing records...")
                result = conn.execute(text("""
                    UPDATE companies 
                    SET prediction_type = 'annual' 
                    WHERE prediction_type IS NULL OR prediction_type = '';
                """))
                print(f"    ✅ Updated {result.rowcount} existing records")
                
                # 6. Make prediction_type NOT NULL after updating
                conn.execute(text("""
                    ALTER TABLE companies 
                    ALTER COLUMN prediction_type SET NOT NULL;
                """))
                
                # Commit transaction
                trans.commit()
                
                print("✅ Database migration completed successfully!")
                print("📊 New quarterly prediction features:")
                print("   - prediction_type: 'annual' or 'quarterly'")
                print("   - sga_margin: SG&A margin for quarterly")
                print("   - return_on_capital: Return on capital for quarterly")
                print("   - logistic_probability: Logistic model result")
                print("   - gbm_probability: GBM model result")
                print("   - Composite unique constraint: symbol + prediction_type + reporting_period")
                
                return True
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("📊 QUARTERLY PREDICTION DATABASE MIGRATION")
    print("=" * 60)
    
    success = migrate_database()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("You can now use both annual and quarterly prediction endpoints.")
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
