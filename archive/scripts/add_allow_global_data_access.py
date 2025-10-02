#!/usr/bin/env python3
"""
Migration script to add allow_global_data_access column to organizations table
Usage:
    python scripts/add_allow_global_data_access.py
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

def add_allow_global_data_access_column():
    """Add the allow_global_data_access column to organizations table"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        logger.info("🚀 Starting database migration...")
        
        # Check if column already exists
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'organizations' 
            AND column_name = 'allow_global_data_access'
        """)
        
        result = db.execute(check_query).fetchone()
        
        if result:
            logger.info("✅ Column 'allow_global_data_access' already exists in organizations table")
            return True
        
        # Add the column
        alter_query = text("""
            ALTER TABLE organizations 
            ADD COLUMN allow_global_data_access BOOLEAN DEFAULT FALSE
        """)
        
        db.execute(alter_query)
        db.commit()
        
        logger.info("✅ Successfully added 'allow_global_data_access' column to organizations table")
        
        # Update existing organizations to have allow_global_data_access = false (default)
        logger.info("📝 Setting default value for existing organizations...")
        
        update_query = text("""
            UPDATE organizations 
            SET allow_global_data_access = FALSE 
            WHERE allow_global_data_access IS NULL
        """)
        
        result = db.execute(update_query)
        db.commit()
        
        logger.info(f"✅ Updated {result.rowcount} existing organizations with default value")
        
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
    logger.info("🔧 Database Migration - Add allow_global_data_access Column")
    logger.info("=" * 60)
    
    # Verify database connection
    try:
        SessionLocal = get_session_local()
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection verified")
        logger.info(f"🔗 Using Database: {DATABASE_URL[:50]}...{DATABASE_URL[-20:]}")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Run migration
    success = add_allow_global_data_access_column()
    
    if not success:
        logger.error("❌ Migration failed")
        sys.exit(1)
    
    logger.info("\n🎉 Migration completed successfully!")
    logger.info("📝 The allow_global_data_access column has been added to the organizations table.")
    logger.info("🔄 You can now restart your FastAPI server to use the updated schema.")

if __name__ == "__main__":
    main()
