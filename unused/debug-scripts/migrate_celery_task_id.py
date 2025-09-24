#!/usr/bin/env python3
"""
Database migration script to add celery_task_id field to BulkUploadJob table
Run this script to update existing databases with the new celery_task_id column
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

def get_database_url():
    """Get database URL from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return database_url

def add_celery_task_id_column():
    """Add celery_task_id column to bulk_upload_jobs table"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        # Check if column already exists
        check_query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'bulk_upload_jobs' 
        AND column_name = 'celery_task_id'
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(check_query))
            if result.fetchone():
                print("✅ celery_task_id column already exists - no migration needed")
                return True
            
            # Add the column
            add_column_query = """
            ALTER TABLE bulk_upload_jobs 
            ADD COLUMN celery_task_id VARCHAR(255)
            """
            
            print("🔧 Adding celery_task_id column to bulk_upload_jobs table...")
            conn.execute(text(add_column_query))
            conn.commit()
            
            # Add index for performance
            add_index_query = """
            CREATE INDEX IF NOT EXISTS idx_bulk_job_celery_task 
            ON bulk_upload_jobs(celery_task_id)
            """
            
            print("📊 Adding index on celery_task_id column...")
            conn.execute(text(add_index_query))
            conn.commit()
            
            print("✅ Migration completed successfully!")
            return True
            
    except (OperationalError, ProgrammingError) as e:
        print(f"❌ Database error during migration: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during migration: {str(e)}")
        return False

def verify_migration():
    """Verify that the migration was successful"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        verify_query = """
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'bulk_upload_jobs' 
        AND column_name = 'celery_task_id'
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(verify_query))
            row = result.fetchone()
            
            if row:
                print(f"✅ Column verified: {row[0]} ({row[1]}, nullable: {row[2]})")
                return True
            else:
                print("❌ Column not found after migration")
                return False
                
    except Exception as e:
        print(f"❌ Error verifying migration: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    print("Adding celery_task_id column to bulk_upload_jobs table")
    print("-" * 50)
    
    # Check if DATABASE_URL is set
    try:
        get_database_url()
    except ValueError as e:
        print(f"❌ {str(e)}")
        print("Please set your DATABASE_URL environment variable")
        sys.exit(1)
    
    # Run migration
    success = add_celery_task_id_column()
    
    if success:
        # Verify migration
        verify_migration()
        print("-" * 50)
        print("✅ Migration completed successfully!")
        print("The bulk upload system will now track Celery task IDs properly.")
    else:
        print("-" * 50)
        print("❌ Migration failed!")
        print("Please check the error messages above and try again.")
        sys.exit(1)
