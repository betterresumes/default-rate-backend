#!/usr/bin/env python3
"""
Professional Database Reset Script for Default Rate Prediction System

This script resets the PostgreSQL database by dropping all tables and recreating them.
It uses the DATABASE_URL from the .env file for connection.

Usage:
    python scripts/reset_database.py

Requirements:
    - PostgreSQL database
    - .env file with DATABASE_URL
    - SQLAlchemy models
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

# Add backend directory to Python path
sys.path.insert(0, str(backend_dir))

try:
    from app.core.database import create_database_engine, Base
    from sqlalchemy import text
    logger.info("✅ Successfully imported database components")
except ImportError as e:
    logger.error(f"❌ Failed to import database components: {e}")
    sys.exit(1)

def verify_database_url():
    """Verify that DATABASE_URL is properly configured"""
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("❌ DATABASE_URL not found in environment variables")
        logger.error("Please check your .env file")
        return False
    
    if not database_url.startswith('postgresql://'):
        logger.error("❌ DATABASE_URL must be a PostgreSQL connection string")
        return False
    
    logger.info(f"✅ Database URL configured: {database_url[:20]}...{database_url[-20:]}")
    return True

def reset_database():
    """Drop all tables and recreate them"""
    try:
        logger.info("🗄️  Starting database reset process...")
        
        # Verify database configuration
        if not verify_database_url():
            return False
        
        # Create engine
        engine = create_database_engine()
        
        # Drop all existing tables (with CASCADE to handle foreign keys)
        logger.info("🔥 Dropping all existing tables...")
        try:
            # For PostgreSQL, we can use CASCADE to drop all foreign key constraints
            with engine.connect() as conn:
                conn.execute(text("DROP SCHEMA public CASCADE;"))
                conn.execute(text("CREATE SCHEMA public;"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
                conn.commit()
            logger.info("✅ All tables and constraints dropped successfully")
        except Exception as e:
            logger.warning(f"⚠️  CASCADE drop failed, trying metadata drop: {e}")
            Base.metadata.drop_all(bind=engine)
            logger.info("✅ All tables dropped using metadata")
        
        # Create all tables with current schema
        logger.info("🏗️  Creating tables with current schema...")
        Base.metadata.create_all(bind=engine)
        logger.info("✅ All tables created successfully")
        
        logger.info("🎉 Database reset completed successfully!")
        logger.info("📋 Database is now ready for fresh data setup")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        return False

def main():
    """Main function"""
    logger.info("=" * 60)
    logger.info("🚀 Default Rate Prediction System - Database Reset")
    logger.info("=" * 60)
    
    # Confirm with user
    print("\n⚠️  WARNING: This will DELETE ALL DATA in the database!")
    print("📊 All tables, users, organizations, and predictions will be removed.")
    
    confirmation = input("\n❓ Are you sure you want to continue? (type 'YES' to proceed): ")
    
    if confirmation != 'YES':
        logger.info("❌ Database reset cancelled by user")
        return
    
    # Perform reset
    success = reset_database()
    
    if success:
        logger.info("\n✅ Next steps:")
        logger.info("1. Run 'python scripts/setup_application_data.py' to create default data")
        logger.info("2. Start your application server")
        logger.info("3. Import the Postman collection for API testing")
    else:
        logger.error("\n❌ Database reset failed. Please check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
