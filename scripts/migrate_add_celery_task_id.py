#!/usr/bin/env python3
"""
Database migration to add celery_task_id field to bulk_upload_jobs table
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Get database URL
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("❌ DATABASE_URL environment variable is not set")
    print("Please ensure you have a .env file with DATABASE_URL defined")
    sys.exit(1)


def migrate_add_celery_task_id():
    """Add celery_task_id column to bulk_upload_jobs table"""
    
    # Create database engine
    engine = create_engine(DATABASE_URL)
    
    try:
        with engine.connect() as connection:
            # Check if column already exists
            result = connection.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'bulk_upload_jobs' 
                AND column_name = 'celery_task_id'
            """))
            
            if result.fetchone():
                print("✅ celery_task_id column already exists")
                return
            
            # Add the column
            connection.execute(text("""
                ALTER TABLE bulk_upload_jobs 
                ADD COLUMN celery_task_id VARCHAR(255)
            """))
            
            # Add index for performance
            connection.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_bulk_job_celery_task 
                ON bulk_upload_jobs(celery_task_id)
            """))
            
            connection.commit()
            print("✅ Successfully added celery_task_id column and index")
        
    except Exception as e:
        print(f"❌ Error adding celery_task_id column: {str(e)}")
        raise


if __name__ == "__main__":
    print("🔄 Adding celery_task_id field to bulk_upload_jobs table...")
    migrate_add_celery_task_id()
    print("✅ Migration completed!")
