#!/usr/bin/env python3
"""
Database setup and migration script for Neon PostgreSQL
Run this after deployment to set up your database schema
"""

import asyncio
import os
import sys
from pathlib import Path

# Add app to path
sys.path.append(str(Path(__file__).parent.parent))

import asyncpg
from sqlalchemy import create_engine, text
from app.core.database import Base, engine
from app.core.config import settings

async def test_connection():
    """Test database connection"""
    try:
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            print("❌ DATABASE_URL not found in environment variables")
            return False
            
        print(f"🔗 Testing connection to database...")
        conn = await asyncpg.connect(database_url)
        result = await conn.fetchval('SELECT version()')
        print(f"✅ Database connected successfully!")
        print(f"📊 PostgreSQL version: {result}")
        await conn.close()
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def create_tables():
    """Create database tables"""
    try:
        print("🏗️ Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create tables: {str(e)}")
        return False

def run_initial_data_setup():
    """Run initial data setup"""
    try:
        print("📊 Setting up initial data...")
        
        # Import and run setup script if it exists
        try:
            from scripts.setup_application_data import main as setup_main
            setup_main()
            print("✅ Initial data setup completed!")
        except ImportError:
            print("⚠️ No initial data setup script found, skipping...")
        except Exception as e:
            print(f"⚠️ Initial data setup failed: {str(e)}")
            
        return True
    except Exception as e:
        print(f"❌ Initial data setup failed: {str(e)}")
        return False

async def main():
    """Main setup function"""
    print("🚀 Starting database setup for Railway + Neon PostgreSQL...")
    
    # Test connection
    if not await test_connection():
        print("❌ Cannot proceed without database connection")
        sys.exit(1)
    
    # Create tables
    if not create_tables():
        print("❌ Cannot proceed without database tables")
        sys.exit(1)
    
    # Setup initial data
    run_initial_data_setup()
    
    print("🎉 Database setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Verify your Railway app is running")
    print("2. Test API endpoints")
    print("3. Check Railway logs for any issues")

if __name__ == "__main__":
    asyncio.run(main())
