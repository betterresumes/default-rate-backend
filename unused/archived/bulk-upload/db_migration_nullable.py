#!/usr/bin/env python3
"""
Database Migration Script
Updates AnnualPrediction table to allow NULL values in financial ratio columns.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from src.database import get_database_url
from sqlalchemy import create_engine, text
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the database migration to allow NULL values in financial ratios"""
    
    try:
        # Create database connection
        database_url = get_database_url()
        if not database_url:
            logger.error("❌ DATABASE_URL not found in environment variables")
            return False
            
        engine = create_engine(database_url)
        
        logger.info("🚀 Starting database migration...")
        logger.info("📝 Making financial ratio columns nullable in annual_predictions table")
        
        # SQL commands to alter table constraints
        migration_sql = [
            "ALTER TABLE annual_predictions ALTER COLUMN long_term_debt_to_total_capital DROP NOT NULL;",
            "ALTER TABLE annual_predictions ALTER COLUMN total_debt_to_ebitda DROP NOT NULL;", 
            "ALTER TABLE annual_predictions ALTER COLUMN net_income_margin DROP NOT NULL;",
            "ALTER TABLE annual_predictions ALTER COLUMN ebit_to_interest_expense DROP NOT NULL;",
            "ALTER TABLE annual_predictions ALTER COLUMN return_on_assets DROP NOT NULL;"
        ]
        
        # Execute migration
        with engine.connect() as connection:
            transaction = connection.begin()
            
            try:
                for i, sql in enumerate(migration_sql, 1):
                    logger.info(f"🔄 Executing step {i}/5: {sql.split()[4]} column...")
                    connection.execute(text(sql))
                
                transaction.commit()
                logger.info("✅ Migration completed successfully!")
                logger.info("📊 Financial ratio columns can now accept NULL values")
                return True
                
            except Exception as e:
                transaction.rollback()
                logger.error(f"❌ Migration failed: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Failed to connect to database: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        logger.info("🔍 Verifying migration...")
        
        # Query to check column constraints
        verify_sql = """
        SELECT column_name, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'annual_predictions' 
        AND column_name IN (
            'long_term_debt_to_total_capital',
            'total_debt_to_ebitda', 
            'net_income_margin',
            'ebit_to_interest_expense',
            'return_on_assets'
        )
        ORDER BY column_name;
        """
        
        with engine.connect() as connection:
            result = connection.execute(text(verify_sql))
            rows = result.fetchall()
            
            logger.info("📋 Column nullability status:")
            all_nullable = True
            
            for row in rows:
                column_name = row[0]
                is_nullable = row[1]
                status = "✅ NULLABLE" if is_nullable == 'YES' else "❌ NOT NULL"
                logger.info(f"  {column_name}: {status}")
                
                if is_nullable != 'YES':
                    all_nullable = False
            
            if all_nullable:
                logger.info("✅ Migration verification successful - all columns are nullable!")
                return True
            else:
                logger.error("❌ Migration verification failed - some columns are still NOT NULL")
                return False
                
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🔧 DATABASE MIGRATION FOR NULL VALUES")
    logger.info("=" * 60)
    
    # Run migration
    if not run_migration():
        logger.error("💥 Migration failed!")
        sys.exit(1)
    
    # Verify migration
    if not verify_migration():
        logger.error("💥 Migration verification failed!")
        sys.exit(1)
    
    logger.info("=" * 60)
    logger.info("🎉 DATABASE MIGRATION COMPLETED SUCCESSFULLY!")
    logger.info("=" * 60)
    logger.info("📝 You can now run bulk predictions with NULL values")
    logger.info("🚀 Run: python3 bulk_annual_predictions.py")

if __name__ == "__main__":
    main()
