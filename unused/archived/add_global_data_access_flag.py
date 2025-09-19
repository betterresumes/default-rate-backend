#!/usr/bin/env python3
"""
Migration script to add allow_global_data_access column to organizations table
Run this script to update existing database schema
"""

from sqlalchemy import create_engine, text
import os
from app.core.database import get_database_url

def add_global_data_access_column():
    """Add allow_global_data_access column to organizations table"""
    try:
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check if column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'organizations' 
                AND column_name = 'allow_global_data_access'
            """))
            
            if result.fetchone():
                print("✅ Column 'allow_global_data_access' already exists in organizations table")
                return
            
            # Add the new column
            conn.execute(text("""
                ALTER TABLE organizations 
                ADD COLUMN allow_global_data_access BOOLEAN DEFAULT FALSE
            """))
            
            # Update existing organizations to have global access disabled by default
            # You can change this logic based on your business requirements
            conn.execute(text("""
                UPDATE organizations 
                SET allow_global_data_access = FALSE 
                WHERE allow_global_data_access IS NULL
            """))
            
            conn.commit()
            print("✅ Successfully added 'allow_global_data_access' column to organizations table")
            print("📝 All existing organizations have global data access disabled by default")
            print("💡 Use the organization management API to enable global access for specific organizations")
            
    except Exception as e:
        print(f"❌ Error adding column: {e}")
        raise

if __name__ == "__main__":
    print("🔧 Adding global data access control to organizations...")
    add_global_data_access_column()
    print("✅ Migration completed successfully!")
