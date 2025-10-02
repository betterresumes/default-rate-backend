#!/usr/bin/env python3
"""
Quick fix script to update existing organizations with allow_global_data_access=False
Usage:
    python scripts/fix_existing_organizations.py
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

def fix_existing_organizations():
    """Update existing organizations to have allow_global_data_access=False"""
    SessionLocal = get_session_local()
    db = SessionLocal()
    
    try:
        logger.info("🚀 Fixing existing organizations...")
        
        # Update all organizations that have NULL allow_global_data_access
        update_query = text("""
            UPDATE organizations 
            SET allow_global_data_access = FALSE 
            WHERE allow_global_data_access IS NULL
        """)
        
        result = db.execute(update_query)
        db.commit()
        
        updated_count = result.rowcount
        logger.info(f"✅ Updated {updated_count} organizations with allow_global_data_access=False")
        
        # Verify the fix
        verify_query = text("""
            SELECT COUNT(*) as total, 
                   COUNT(CASE WHEN allow_global_data_access IS NULL THEN 1 END) as null_count
            FROM organizations
        """)
        
        result = db.execute(verify_query).fetchone()
        logger.info(f"📊 Total organizations: {result.total}, NULL values: {result.null_count}")
        
        if result.null_count == 0:
            logger.info("🎉 All organizations now have valid allow_global_data_access values!")
        else:
            logger.warning(f"⚠️ Still have {result.null_count} organizations with NULL values")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Fix failed: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🔧 Fix Existing Organizations - allow_global_data_access")
    logger.info("=" * 60)
    
    # Verify database connection
    try:
        SessionLocal = get_session_local()
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection verified")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        sys.exit(1)
    
    # Fix organizations
    success = fix_existing_organizations()
    
    if success:
        logger.info("✅ Fix completed successfully")
    else:
        logger.error("❌ Fix failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
