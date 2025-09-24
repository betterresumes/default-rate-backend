#!/usr/bin/env python3
"""
Migration script to add celery_task_id column to bulk_upload_jobs table
Usage:
    python scripts/add_celery_task_id_column.py
"""

import sys
import logging
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to the path to import app modules
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Database URL
DATABASE_URL = "postgresql://neondb_owner:npg_FRS5ptsg3QcE@ep-snowy-darkness-adw0r2ai-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def get_session_local():
    """Create database session using the specific DATABASE_URL"""
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal

def add_celery_task_id_column():
    """Add celery_task_id column to bulk_upload_jobs table"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        logger.info("🚀 Adding celery_task_id column to bulk_upload_jobs table...")
        
        # Check if column already exists
        check_column_query = text("""
            SELECT COUNT(*)
            FROM information_schema.columns 
            WHERE table_name='bulk_upload_jobs' 
            AND column_name='celery_task_id'
        """)
        
        result = db.execute(check_column_query).fetchone()
        column_exists = result[0] > 0
        
        if column_exists:
            logger.info("✅ Column celery_task_id already exists in bulk_upload_jobs table")
            return True
        
        # Add the column
        add_column_query = text("""
            ALTER TABLE bulk_upload_jobs 
            ADD COLUMN celery_task_id VARCHAR(255);
        """)
        
        db.execute(add_column_query)
        db.commit()
        
        # Add index for better performance
        add_index_query = text("""
            CREATE INDEX IF NOT EXISTS ix_bulk_upload_jobs_celery_task_id 
            ON bulk_upload_jobs (celery_task_id);
        """)
        
        db.execute(add_index_query)
        db.commit()
        
        logger.info("✅ Successfully added celery_task_id column with index to bulk_upload_jobs table")
        
        # Verify the column was added
        verify_query = text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name='bulk_upload_jobs' 
            AND column_name='celery_task_id'
        """)
        
        result = db.execute(verify_query).fetchone()
        if result:
            logger.info(f"✅ Verification: Column '{result[0]}' added with type '{result[1]}', nullable: {result[2]}")
        else:
            logger.error("❌ Verification failed: Column not found after creation")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🏗️  Adding celery_task_id Column Migration")
    logger.info("=" * 60)
    
    success = add_celery_task_id_column()
    
    if success:
        logger.info("🎉 Migration completed successfully!")
        logger.info("You can now use bulk upload functionality with Celery task tracking.")
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
