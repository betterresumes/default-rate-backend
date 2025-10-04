#!/usr/bin/env python3
"""
Quick Database Inspection Script

This script connects to your database and shows what's currently there.
Works with any PostgreSQL database (local or RDS).
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment
from dotenv import load_dotenv
load_dotenv(project_root / '.env')

try:
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.orm import sessionmaker
    import psycopg2
except ImportError as e:
    print(f"❌ Missing dependencies: {e}")
    print("Install with: pip install sqlalchemy psycopg2-binary python-dotenv")
    sys.exit(1)

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    print("Make sure your .env file contains DATABASE_URL")
    sys.exit(1)

def inspect_database():
    """Inspect database structure and content"""
    print("🔍 DATABASE INSPECTION")
    print("=" * 40)
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL, echo=False)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()
        
        # Database info
        print("📊 Database Connection:")
        result = db.execute(text("SELECT current_database(), current_user, version()"))
        db_info = result.fetchone()
        print(f"   Database: {db_info[0]}")
        print(f"   User: {db_info[1]}")
        print(f"   Version: {db_info[2]}")
        
        # List all tables
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"\n📋 Tables Found: {len(tables)}")
        if tables:
            for table in sorted(tables):
                try:
                    # Get row count
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"   {table}: {count:,} rows")
                except Exception as e:
                    print(f"   {table}: Error counting rows ({str(e)[:50]})")
        else:
            print("   No tables found!")
        
        # Check for our main tables
        main_tables = ['users', 'tenants', 'organizations', 'companies', 'annual_predictions', 'quarterly_predictions']
        existing_main_tables = [t for t in main_tables if t in tables]
        
        if existing_main_tables:
            print(f"\n🎯 Main Application Tables:")
            for table in existing_main_tables:
                try:
                    result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    print(f"   ✅ {table}: {count:,} records")
                except Exception:
                    print(f"   ❌ {table}: Cannot access")
        else:
            print(f"\n⚠️  Main application tables not found!")
            print("   You may need to run database migrations first.")
        
        # Check for admin users
        if 'users' in tables:
            print(f"\n👑 Admin Users:")
            try:
                result = db.execute(text("""
                    SELECT email, username, role, is_active 
                    FROM users 
                    WHERE role IN ('super_admin', 'tenant_admin', 'admin')
                    ORDER BY role, email
                """))
                admins = result.fetchall()
                
                if admins:
                    for admin in admins:
                        status = "🟢" if admin[3] else "🔴"
                        print(f"   {status} {admin[0]} ({admin[1]}) - {admin[2]}")
                else:
                    print("   No admin users found")
            except Exception as e:
                print(f"   Error checking admin users: {e}")
        
        # Database size
        try:
            result = db.execute(text("""
                SELECT pg_size_pretty(pg_database_size(current_database())) as db_size
            """))
            db_size = result.scalar()
            print(f"\n💾 Database Size: {db_size}")
        except Exception:
            print(f"\n💾 Database Size: Unable to determine")
        
        print(f"\n✅ Database inspection complete!")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check if your DATABASE_URL is correct")
        print("2. Ensure the database server is running")
        print("3. Verify network connectivity")
        print("4. Check if you need to access via bastion/VPN")
        return False

def test_raw_connection():
    """Test raw PostgreSQL connection"""
    print("\n🧪 RAW CONNECTION TEST")
    print("=" * 30)
    
    # Parse DATABASE_URL
    url = DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "")
    
    try:
        parts = url.split("@")
        credentials = parts[0]
        host_db = parts[1]
        
        username, password = credentials.split(":")
        host_port, db_params = host_db.split("/", 1)
        
        if ":" in host_port:
            host, port = host_port.split(":")
        else:
            host, port = host_port, "5432"
        
        database = db_params.split("?")[0]
        
        print(f"Host: {host}")
        print(f"Port: {port}")
        print(f"Database: {database}")
        print(f"Username: {username}")
        
        # Test connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password
        )
        
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()
        print(f"✅ Connection successful!")
        print(f"PostgreSQL Version: {version[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Raw connection failed: {e}")
        return False

def main():
    """Main function"""
    print("🔍 DATABASE INSPECTOR")
    print("=" * 30)
    
    # Test raw connection first
    if test_raw_connection():
        # If raw connection works, do full inspection
        inspect_database()
    else:
        print("\n❌ Cannot connect to database")
        print("Please check your connection and try again")

if __name__ == "__main__":
    main()
