#!/usr/bin/env python3
"""
Database Reset Script
====================

This script only resets the database - drops all tables and recreates them.
Use setup_application.py after this to populate with initial data.
"""

import os
import sys
from sqlalchemy import create_engine

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base, get_database_url

def reset_database():
    """Drop all tables and recreate them"""
    try:
        print("🔄 Starting database reset...")
        
        database_url = get_database_url()
        engine = create_engine(database_url, echo=True)
        
        print("🗑️  Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        
        print("🏗️  Creating fresh tables with new 5-role schema...")
        Base.metadata.create_all(bind=engine)
        
        print("✅ Database reset complete!")
        print("📝 Next step: Run 'python setup_application.py' to populate with initial data")
        
    except Exception as e:
        print(f"❌ Error during database reset: {str(e)}")
        raise

if __name__ == "__main__":
    reset_database()
