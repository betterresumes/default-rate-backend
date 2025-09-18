#!/usr/bin/env python3

"""
Database Schema Checker
Checks for duplicate fields and validates the User table structure
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import create_database_engine, User
from sqlalchemy import inspect

def check_database_schema():
    """Check the current database schema for the User table"""
    print("🔍 Checking Database Schema...")
    
    try:
        engine = create_database_engine()
        inspector = inspect(engine)
        
        # Get User table columns
        if "users" in inspector.get_table_names():
            columns = inspector.get_columns("users")
            print(f"\n📊 Found {len(columns)} columns in 'users' table:")
            
            tenant_fields = []
            org_fields = []
            
            for col in columns:
                print(f"  - {col['name']}: {col['type']} {'(nullable)' if col['nullable'] else '(required)'}")
                
                # Check for duplicate tenant fields
                if 'tenant' in col['name'].lower():
                    tenant_fields.append(col['name'])
                
                # Check for duplicate organization fields  
                if 'org' in col['name'].lower():
                    org_fields.append(col['name'])
            
            print(f"\n🏢 Tenant-related fields: {tenant_fields}")
            print(f"🏛️ Organization-related fields: {org_fields}")
            
            # Check for duplicates
            if len(tenant_fields) > 1:
                print(f"⚠️  WARNING: Multiple tenant fields detected: {tenant_fields}")
            
            if len(org_fields) > 1:
                print(f"⚠️  WARNING: Multiple organization fields detected: {org_fields}")
            
            # Check indexes
            indexes = inspector.get_indexes("users")
            print(f"\n📇 Indexes ({len(indexes)}):")
            for idx in indexes:
                print(f"  - {idx['name']}: {idx['column_names']}")
                
            return True
        else:
            print("❌ 'users' table not found!")
            print("Available tables:", inspector.get_table_names())
            return False
            
    except Exception as e:
        print(f"❌ Error checking schema: {e}")
        return False

if __name__ == "__main__":
    check_database_schema()
