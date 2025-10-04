#!/usr/bin/env python3
"""
Quick Database Reset using SQLAlchemy
Usage: python scripts/quick_reset_db.py
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the parent directory to Python path to import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.core.database import User, Tenant, Organization, OrganizationMemberWhitelist, Company, AnnualPrediction, QuarterlyPrediction, BulkUploadJob
    from app.core.config import get_config
except ImportError as e:
    print(f"❌ Could not import required modules: {e}")
    print("Make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

def get_database_url():
    """Get database URL from config or environment"""
    config = get_config()
    
    if hasattr(config, 'DATABASE_URL') and config.DATABASE_URL:
        return config.DATABASE_URL
    
    # Fallback to environment variable
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    print("❌ No DATABASE_URL found in config or environment variables")
    print("Please set DATABASE_URL environment variable or update config")
    sys.exit(1)

def confirm_reset() -> bool:
    """Ask user for confirmation"""
    print("\n" + "=" * 60)
    print("⚠️  QUICK DATABASE RESET")
    print("=" * 60)
    print("This will delete ALL DATA from these tables:")
    print("• users")
    print("• tenants") 
    print("• organizations")
    print("• organization_member_whitelists")
    print("• companies")
    print("• annual_predictions")
    print("• quarterly_predictions")
    print("• bulk_upload_jobs")
    print("• Any other application tables")
    print("\n❌ This operation CANNOT be undone!")
    print("=" * 60)
    
    response = input("\nType 'RESET' to confirm: ").strip()
    return response == 'RESET'

def reset_database_data():
    """Reset all data in the database"""
    
    if not confirm_reset():
        print("❌ Operation cancelled.")
        return False
    
    try:
        database_url = get_database_url()
        logger.info("🔌 Connecting to database...")
        
        engine = create_engine(database_url, echo=False)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Get table counts before reset
        logger.info("📊 Getting current data counts...")
        
        tables_to_reset = [
            ("bulk_upload_jobs", BulkUploadJob),
            ("quarterly_predictions", QuarterlyPrediction),
            ("annual_predictions", AnnualPrediction),
            ("companies", Company),
            ("organization_member_whitelists", OrganizationMemberWhitelist),
            ("users", User),
            ("organizations", Organization),
            ("tenants", Tenant),
        ]
        
        initial_counts = {}
        for table_name, model in tables_to_reset:
            try:
                count = session.query(model).count()
                initial_counts[table_name] = count
                print(f"   {table_name}: {count:,} records")
            except Exception as e:
                initial_counts[table_name] = f"Error: {e}"
                print(f"   {table_name}: Error counting - {e}")
        
        total_records = sum(count for count in initial_counts.values() if isinstance(count, int))
        print(f"\n📊 Total records to delete: {total_records:,}")
        
        if total_records == 0:
            print("ℹ️ Database is already empty.")
            return True
        
        # Start deletion
        logger.info("🗑️ Starting data deletion...")
        
        # Delete in reverse dependency order
        deleted_counts = {}
        for table_name, model in tables_to_reset:
            try:
                # Delete all records
                deleted = session.query(model).delete()
                deleted_counts[table_name] = deleted
                session.commit()
                logger.info(f"✅ Deleted {deleted:,} records from {table_name}")
            except Exception as e:
                session.rollback()
                logger.error(f"❌ Failed to delete from {table_name}: {e}")
                raise
        
        # Reset sequences (PostgreSQL specific)
        logger.info("🔄 Resetting ID sequences...")
        try:
            # Get all sequences and reset them
            result = session.execute(text("""
                SELECT sequence_name 
                FROM information_schema.sequences 
                WHERE sequence_schema = 'public'
            """))
            
            sequences = [row[0] for row in result]
            
            for seq_name in sequences:
                session.execute(text(f"ALTER SEQUENCE {seq_name} RESTART WITH 1"))
                logger.info(f"✅ Reset sequence: {seq_name}")
            
            session.commit()
            
        except Exception as e:
            logger.warning(f"⚠️ Could not reset sequences: {e}")
        
        # Verify deletion
        logger.info("✅ Verifying deletion...")
        final_total = 0
        for table_name, model in tables_to_reset:
            try:
                count = session.query(model).count()
                final_total += count
                if count > 0:
                    logger.warning(f"⚠️ {table_name} still has {count} records")
            except Exception as e:
                logger.error(f"❌ Error verifying {table_name}: {e}")
        
        if final_total == 0:
            print("\n🎉 SUCCESS: Database reset completed!")
            print("📊 All application data has been deleted")
            print("🔄 All sequences reset to start from 1")
            print("🏗️ Database structure preserved")
            
            # Show summary
            print(f"\n📋 DELETION SUMMARY:")
            total_deleted = 0
            for table_name, count in deleted_counts.items():
                print(f"   {table_name}: {count:,} records deleted")
                total_deleted += count
            print(f"   TOTAL: {total_deleted:,} records deleted")
        else:
            logger.warning(f"⚠️ Warning: {final_total} records still remain")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        if 'session' in locals():
            session.rollback()
        return False
        
    finally:
        if 'session' in locals():
            session.close()
        logger.info("🔌 Database connection closed")

def main():
    """Main entry point"""
    print("🗄️ AccuNode Quick Database Reset")
    print("=" * 40)
    print("🎯 Reset all application data while preserving structure")
    
    success = reset_database_data()
    
    if success:
        print("\n✅ Database reset completed successfully!")
        print("🚀 You can now run the tenant setup script to create fresh data.")
    else:
        print("\n❌ Database reset failed. Check logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
