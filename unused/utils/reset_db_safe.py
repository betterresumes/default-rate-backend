#!/usr/bin/env python3
"""
Database Reset Script - Handles Circular Dependencies
====================================================

This script safely resets the database by handling foreign key constraints.
"""

import os
import sys
from sqlalchemy import create_engine, text

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Manually load .env file if dotenv is not available
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#') and '=' in line:
                    key, value = line.strip().split('=', 1)
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    os.environ[key] = value

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, get_database_url

def create_engine_and_session():
    """Create database engine"""
    database_url = get_database_url()
    engine = create_engine(database_url, echo=True)
    return engine

def reset_database_safe(engine):
    """Safely reset database by handling foreign key constraints"""
    print("🗑️  Safely dropping all existing tables...")
    
    with engine.connect() as connection:
        # Start transaction
        trans = connection.begin()
        
        try:
            # Drop all tables manually in the correct order to avoid circular dependencies
            print("   Dropping prediction tables...")
            connection.execute(text("DROP TABLE IF EXISTS quarterly_predictions CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS annual_predictions CASCADE"))
            
            print("   Dropping company table...")
            connection.execute(text("DROP TABLE IF EXISTS companies CASCADE"))
            
            print("   Dropping whitelist table...")
            connection.execute(text("DROP TABLE IF EXISTS organization_member_whitelist CASCADE"))
            
            print("   Dropping user table...")
            connection.execute(text("DROP TABLE IF EXISTS users CASCADE"))
            
            print("   Dropping organization table...")
            connection.execute(text("DROP TABLE IF EXISTS organizations CASCADE"))
            
            print("   Dropping tenant table...")
            connection.execute(text("DROP TABLE IF EXISTS tenants CASCADE"))
            
            # Commit the transaction
            trans.commit()
            print("✅ All tables dropped successfully!")
            
        except Exception as e:
            trans.rollback()
            print(f"❌ Error dropping tables: {e}")
            raise
    
    print("🏗️  Creating fresh tables with new schema...")
    Base.metadata.create_all(bind=engine)
    print("✅ Database schema reset complete!")

def main():
    """Main function to reset database"""
    try:
        print("🔄 Starting safe database reset...")
        
        # Create engine
        engine = create_engine_and_session()
        
        # Reset database safely
        reset_database_safe(engine)
        
        print("✅ Database reset completed successfully!")
        print("🚀 You can now run setup_data.py to populate with sample data")
        
    except Exception as e:
        print(f"❌ Error during database reset: {str(e)}")
        raise

if __name__ == "__main__":
    main()
