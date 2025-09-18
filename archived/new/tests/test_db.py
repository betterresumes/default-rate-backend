#!/usr/bin/env python3
"""
Test database connection and create tables
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Add the src directory to the path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def test_connection():
    """Test database connection"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set!")
        return False
    
    try:
        print("🔄 Testing database connection...")
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            
        # Check existing tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            print(f"📋 Existing tables: {tables}")
            
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def create_tables():
    """Create new tables using the database.py models"""
    try:
        print("🏗️  Creating tables...")
        from database import Base, engine
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        
        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result]
            print(f"📋 Current tables: {tables}")
            
        return True
        
    except Exception as e:
        print(f"❌ Table creation failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Database Setup and Migration")
    print("=" * 50)
    
    # Test connection
    if not test_connection():
        sys.exit(1)
    
    # Create tables
    if not create_tables():
        sys.exit(1)
    
    print("=" * 50)
    print("🎉 Database setup completed successfully!")
