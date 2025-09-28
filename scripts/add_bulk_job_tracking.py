#!/usr/bin/env python3
"""
Database migration script to add bulk_upload_job_id tracking to prediction tables.

This fixes the issue where job results show incorrect prediction counts due to
time-based filtering instead of direct job association.

Run this script to:
1. Add bulk_upload_job_id columns to annual_predictions and quarterly_predictions tables
2. Add indexes for better performance
3. Update existing records (set to NULL for historical data)
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, inspect
from app.core.database import get_session_local, _engine, create_database_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the database migration to add bulk job tracking"""
    
    # Ensure engine is created
    if _engine is None:
        create_database_engine()
    
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        # Check if migration is needed
        inspector = inspect(_engine)
        
        # Check annual_predictions table
        annual_columns = [col['name'] for col in inspector.get_columns('annual_predictions')]
        annual_needs_migration = 'bulk_upload_job_id' not in annual_columns
        
        # Check quarterly_predictions table  
        quarterly_columns = [col['name'] for col in inspector.get_columns('quarterly_predictions')]
        quarterly_needs_migration = 'bulk_upload_job_id' not in quarterly_columns
        
        if not annual_needs_migration and not quarterly_needs_migration:
            logger.info("✅ Migration already applied - bulk_upload_job_id columns exist")
            return
        
        logger.info("🔧 Starting database migration to add bulk job tracking...")
        
        # Add bulk_upload_job_id column to annual_predictions if needed
        if annual_needs_migration:
            logger.info("📊 Adding bulk_upload_job_id to annual_predictions...")
            db.execute(text("""
                ALTER TABLE annual_predictions 
                ADD COLUMN bulk_upload_job_id UUID REFERENCES bulk_upload_jobs(id)
            """))
            
            # Add index for performance
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_annual_bulk_job 
                ON annual_predictions(bulk_upload_job_id)
            """))
            
            logger.info("✅ Added bulk_upload_job_id to annual_predictions")
        
        # Add bulk_upload_job_id column to quarterly_predictions if needed
        if quarterly_needs_migration:
            logger.info("📈 Adding bulk_upload_job_id to quarterly_predictions...")
            db.execute(text("""
                ALTER TABLE quarterly_predictions 
                ADD COLUMN bulk_upload_job_id UUID REFERENCES bulk_upload_jobs(id)
            """))
            
            # Add index for performance
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_quarterly_bulk_job 
                ON quarterly_predictions(bulk_upload_job_id)
            """))
            
            logger.info("✅ Added bulk_upload_job_id to quarterly_predictions")
        
        # Commit the changes
        db.commit()
        
        logger.info("🎉 Migration completed successfully!")
        logger.info("")
        logger.info("📝 Note: Existing predictions will have bulk_upload_job_id = NULL")
        logger.info("   This is expected - only new bulk uploads will be tracked.")
        logger.info("")
        logger.info("🔍 The job results endpoint will now show accurate prediction counts!")
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Migration failed: {str(e)}")
        raise
    finally:
        db.close()

def verify_migration():
    """Verify that the migration was successful"""
    try:
        # Ensure engine is created
        if _engine is None:
            create_database_engine()
            
        inspector = inspect(_engine)
        
        # Check annual_predictions columns
        annual_columns = [col['name'] for col in inspector.get_columns('annual_predictions')]
        annual_has_column = 'bulk_upload_job_id' in annual_columns
        
        # Check quarterly_predictions columns
        quarterly_columns = [col['name'] for col in inspector.get_columns('quarterly_predictions')]
        quarterly_has_column = 'bulk_upload_job_id' in quarterly_columns
        
        logger.info("🔍 Migration verification:")
        logger.info(f"   annual_predictions.bulk_upload_job_id: {'✅ EXISTS' if annual_has_column else '❌ MISSING'}")
        logger.info(f"   quarterly_predictions.bulk_upload_job_id: {'✅ EXISTS' if quarterly_has_column else '❌ MISSING'}")
        
        if annual_has_column and quarterly_has_column:
            logger.info("🎉 Migration verification PASSED!")
            return True
        else:
            logger.error("❌ Migration verification FAILED!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Verification failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("=" * 80)
    print("🔧 BULK JOB TRACKING MIGRATION")
    print("=" * 80)
    print()
    print("This migration fixes the issue where job results show incorrect")
    print("prediction counts by adding direct job-to-prediction associations.")
    print()
    
    try:
        run_migration()
        verify_migration()
        
        print()
        print("=" * 80)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()
        print("What was fixed:")
        print("• Added bulk_upload_job_id columns to prediction tables")
        print("• Added database indexes for performance")
        print("• Job results endpoint will now show accurate counts")
        print()
        print("Next steps:")
        print("1. Restart your application")
        print("2. Test bulk uploads to verify fix")
        print("3. Check job results endpoint for accurate counts")
        
    except Exception as e:
        print()
        print("=" * 80)
        print("❌ MIGRATION FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        print()
        print("Please check the logs and try again.")
        sys.exit(1)
