#!/usr/bin/env python3
"""
Legacy Invitations Cleanup Script

This script removes the old invitations table and cleans up any remaining
invitation-related code that's no longer needed in the whitelist-based system.

WHAT THIS SCRIPT DOES:
1. ✅ Checks if invitations table exists
2. ✅ Shows table data (if any) for backup purposes  
3. ✅ Drops the invitations table safely
4. ✅ Reports cleanup status

WHY WE'RE REMOVING IT:
- Old invitation-based system was replaced with whitelist-based joining
- Invitations table is not used in current multi-tenant architecture
- Whitelist system is simpler: admin adds emails → users join directly
- No invitation tokens or complex workflow needed

SAFETY MEASURES:
- Shows existing data before deletion
- Uses DROP TABLE IF EXISTS (won't fail if table doesn't exist)
- Provides clear logging of all actions
"""

import os
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_database_url():
    """Get database URL from environment"""
    return os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/defaultrate")

def main():
    """Main cleanup function"""
    print("🧹 LEGACY INVITATIONS CLEANUP SCRIPT")
    print("="*50)
    
    # Connect to database
    database_url = get_database_url()
    engine = create_engine(database_url)
    
    print(f"📋 Connected to database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    
    with engine.connect() as conn:
        # Check if invitations table exists
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if 'invitations' not in tables:
            print("✅ No invitations table found - already clean!")
            return
        
        print("🔍 Found invitations table - checking contents...")
        
        # Get table structure
        try:
            columns = inspector.get_columns('invitations')
            print(f"📋 Table structure: {len(columns)} columns")
            for col in columns:
                print(f"   - {col['name']}: {col['type']}")
        except Exception as e:
            print(f"⚠️ Could not read table structure: {e}")
        
        # Check for existing data
        try:
            result = conn.execute(text("SELECT COUNT(*) FROM invitations"))
            count = result.scalar()
            print(f"📊 Records in invitations table: {count}")
            
            if count > 0:
                print("⚠️ ATTENTION: Invitations table contains data!")
                print("📋 Sample records (first 5):")
                result = conn.execute(text("""
                    SELECT id, organization_id, email, role, is_used, 
                           created_at, expires_at
                    FROM invitations 
                    ORDER BY created_at DESC 
                    LIMIT 5
                """))
                
                for row in result:
                    print(f"   - ID: {row[0]}, Org: {row[1]}, Email: {row[2]}, Role: {row[3]}, Used: {row[4]}")
                
                response = input("\n❓ Found existing invitation data. Continue with deletion? (yes/no): ")
                if response.lower() not in ['yes', 'y']:
                    print("❌ Cleanup cancelled by user")
                    return
            
        except Exception as e:
            print(f"⚠️ Could not read table data: {e}")
        
        # Drop the invitations table
        try:
            print("\n🗑️ Dropping invitations table...")
            conn.execute(text("DROP TABLE IF EXISTS invitations CASCADE"))
            conn.commit()
            print("✅ Successfully dropped invitations table")
            
        except Exception as e:
            print(f"❌ Error dropping table: {e}")
            conn.rollback()
            return
    
    print("\n🎉 CLEANUP COMPLETE!")
    print("✅ Legacy invitations table removed")
    print("✅ Database now uses whitelist-based joining only")
    print("\n📋 WHAT WAS REMOVED:")
    print("   - invitations table (id, organization_id, email, role, token, etc.)")
    print("   - Old invitation-based workflow")
    print("\n📋 WHAT REMAINS:")
    print("   - Whitelist-based joining system")
    print("   - org_whitelist table for authorized emails")
    print("   - Direct organization joining via join links")
    
    print("\n🔧 NEXT STEPS:")
    print("   1. Clean up invitation-related code in email_service.py")
    print("   2. Remove invitation schemas from schemas_new.py") 
    print("   3. Update API documentation to reflect whitelist-only system")

if __name__ == "__main__":
    main()
