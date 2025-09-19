#!/usr/bin/env python3

"""
Database Migration: Add Bulk Upload Job Tables
Creates the bulk_upload_jobs table for async job tracking
"""

import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

# Add the parent directory to Python path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_database_url, create_database_engine, Base, BulkUploadJob

def migrate_add_bulk_upload_jobs():
    """Add bulk upload job tracking tables"""
    
    print("=" * 60)
    print("BULK UPLOAD JOBS TABLE MIGRATION")
    print("=" * 60)
    
    try:
        # Get database connection
        engine = create_database_engine()
        
        print(f"Connected to database: {get_database_url()}")
        
        # Create the bulk upload jobs table
        print("\n1. Creating bulk_upload_jobs table...")
        
        BulkUploadJob.__table__.create(engine, checkfirst=True)
        
        print("✅ bulk_upload_jobs table created successfully")
        
        # Verify table creation
        print("\n2. Verifying table structure...")
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable 
                FROM information_schema.columns 
                WHERE table_name = 'bulk_upload_jobs' 
                ORDER BY ordinal_position;
            """))
            
            columns = result.fetchall()
            
            if not columns:
                raise Exception("bulk_upload_jobs table was not created properly")
            
            print("Table columns:")
            for col_name, data_type, is_nullable in columns:
                print(f"  - {col_name}: {data_type} {'(nullable)' if is_nullable == 'YES' else '(not null)'}")
        
        print("\n3. Verifying indexes...")
        
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname, indexdef 
                FROM pg_indexes 
                WHERE tablename = 'bulk_upload_jobs';
            """))
            
            indexes = result.fetchall()
            print(f"Found {len(indexes)} indexes on bulk_upload_jobs table")
            for idx_name, idx_def in indexes:
                print(f"  - {idx_name}")
        
        print("\n✅ Migration completed successfully!")
        print("\nNew features added:")
        print("  - Async bulk upload job tracking")
        print("  - Job status monitoring (pending, processing, completed, failed)")
        print("  - Progress tracking (processed/successful/failed rows)")
        print("  - Error logging and details")
        print("  - Organization-scoped job management")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = migrate_add_bulk_upload_jobs()
    if not success:
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("MIGRATION SUMMARY")
    print("=" * 60)
    print("✅ bulk_upload_jobs table created")
    print("✅ Indexes and constraints applied")
    print("✅ Ready for async bulk upload operations")
    print("\nYou can now use:")
    print("  - POST /api/v1/predictions/annual/bulk-upload-async")
    print("  - POST /api/v1/predictions/quarterly/bulk-upload-async") 
    print("  - GET /api/v1/predictions/jobs/{job_id}/status")
    print("  - GET /api/v1/predictions/jobs")
