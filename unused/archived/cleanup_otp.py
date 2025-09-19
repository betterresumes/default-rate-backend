#!/usr/bin/env python3
"""
Remove OTP functionality and clean up database
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set")
    return database_url

def remove_otp_functionality():
    """Remove OTP tokens table and any related data."""
    
    engine = create_engine(get_database_url())
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                print("🗑️  Checking for OTP tokens table...")
                
                # Check if otp_tokens table exists
                result = conn.execute(text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'otp_tokens'
                    );
                """))
                
                table_exists = result.fetchone()[0]
                
                if table_exists:
                    print("📋 Found otp_tokens table, removing...")
                    
                    # Drop the table
                    conn.execute(text("DROP TABLE IF EXISTS otp_tokens CASCADE;"))
                    print("✅ Removed otp_tokens table")
                else:
                    print("✅ No otp_tokens table found")
                
                # Remove any OTP-related columns from users table if they exist
                print("🔍 Checking for OTP-related columns in users table...")
                
                # Check if users table has otp-related columns
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'users' 
                    AND table_schema = 'public'
                    AND column_name LIKE '%otp%' OR column_name LIKE '%verification%';
                """))
                
                otp_columns = [row[0] for row in result.fetchall()]
                
                if otp_columns:
                    print(f"📋 Found OTP-related columns: {otp_columns}")
                    for column in otp_columns:
                        try:
                            conn.execute(text(f"ALTER TABLE users DROP COLUMN IF EXISTS {column};"))
                            print(f"✅ Removed column: {column}")
                        except Exception as e:
                            print(f"⚠️  Could not remove column {column}: {e}")
                else:
                    print("✅ No OTP-related columns found in users table")
                
                # Commit transaction
                trans.commit()
                print("✅ OTP cleanup completed successfully!")
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Error during OTP cleanup: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🧹 Starting OTP cleanup...")
    
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success = remove_otp_functionality()
    
    if success:
        print("\n🎉 OTP cleanup completed!")
        print("✨ Database is now clean and ready for multi-tenant API")
    else:
        print("\n💥 OTP cleanup failed!")
        sys.exit(1)
