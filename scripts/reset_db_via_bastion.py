#!/usr/bin/env python3
"""
Database Reset via Bastion Host
Usage: python scripts/reset_db_via_bastion.py
"""

import subprocess
import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASTION_IP = "52.91.36.2"
BASTION_KEY = "../bastion-access-key.pem"
RDS_ENDPOINT = "accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com"
DB_USER = "accunode_admin"
DB_NAME = "postgres"

def confirm_reset() -> bool:
    """Ask user for confirmation"""
    print("\n" + "=" * 60)
    print("⚠️  DATABASE RESET VIA BASTION HOST")
    print("=" * 60)
    print("This will:")
    print("✗ Connect to RDS via bastion host")
    print("✗ DELETE ALL DATA from application tables")
    print("✗ RESET all sequences")
    print("✗ Cannot be undone")
    print("=" * 60)
    
    response = input("\nType 'CONFIRM RESET' to proceed: ").strip()
    return response == 'CONFIRM RESET'

def run_sql_via_bastion(sql_commands: list, db_password: str) -> bool:
    """Run SQL commands via bastion host"""
    try:
        # Create a temporary SQL file
        sql_content = "\\set ON_ERROR_STOP on\n" + "\n".join(sql_commands)
        
        with open("/tmp/reset_db.sql", "w") as f:
            f.write(sql_content)
        
        # Copy SQL file to bastion host
        logger.info("📤 Copying SQL script to bastion host...")
        scp_cmd = [
            "scp", "-i", BASTION_KEY,
            "/tmp/reset_db.sql",
            f"ubuntu@{BASTION_IP}:/tmp/reset_db.sql"
        ]
        
        result = subprocess.run(scp_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"❌ Failed to copy SQL file: {result.stderr}")
            return False
        
        # Execute SQL via bastion host
        logger.info("🚀 Executing SQL commands via bastion host...")
        
        # Create the psql command
        psql_cmd = f"""
        export PGPASSWORD='{db_password}' && 
        psql -h {RDS_ENDPOINT} -U {DB_USER} -d {DB_NAME} -f /tmp/reset_db.sql
        """
        
        ssh_cmd = [
            "ssh", "-i", BASTION_KEY,
            f"ubuntu@{BASTION_IP}",
            psql_cmd
        ]
        
        result = subprocess.run(ssh_cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info("✅ SQL commands executed successfully")
            print("SQL Output:")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            logger.error(f"❌ SQL execution failed: {result.stderr}")
            if result.stdout:
                print("SQL Output:", result.stdout)
            return False
            
    except Exception as e:
        logger.error(f"❌ Error executing SQL via bastion: {e}")
        return False
    
    finally:
        # Clean up temporary file
        if os.path.exists("/tmp/reset_db.sql"):
            os.remove("/tmp/reset_db.sql")

def generate_reset_sql() -> list:
    """Generate SQL commands to reset the database"""
    return [
        "-- AccuNode Database Reset Script",
        "-- This will delete all data while preserving structure",
        "",
        "-- Disable foreign key checks temporarily", 
        "SET session_replication_role = replica;",
        "",
        "-- Get current table counts",
        "SELECT 'BEFORE RESET - Table Counts:' as info;",
        """
        SELECT 
            schemaname,
            tablename, 
            n_tup_ins - n_tup_del as row_count
        FROM pg_stat_user_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename;
        """,
        "",
        "-- Truncate all tables with CASCADE to handle foreign keys",
        "TRUNCATE TABLE IF EXISTS bulk_upload_jobs RESTART IDENTITY CASCADE;",
        "TRUNCATE TABLE IF EXISTS quarterly_predictions RESTART IDENTITY CASCADE;",
        "TRUNCATE TABLE IF EXISTS annual_predictions RESTART IDENTITY CASCADE;", 
        "TRUNCATE TABLE IF EXISTS companies RESTART IDENTITY CASCADE;",
        "TRUNCATE TABLE IF EXISTS organization_member_whitelists RESTART IDENTITY CASCADE;",
        "TRUNCATE TABLE IF EXISTS users RESTART IDENTITY CASCADE;",
        "TRUNCATE TABLE IF EXISTS organizations RESTART IDENTITY CASCADE;",
        "TRUNCATE TABLE If EXISTS tenants RESTART IDENTITY CASCADE;",
        "",
        "-- Reset all sequences in the public schema",
        """
        DO $$
        DECLARE
            seq_name TEXT;
        BEGIN
            FOR seq_name IN 
                SELECT sequence_name 
                FROM information_schema.sequences 
                WHERE sequence_schema = 'public'
            LOOP
                EXECUTE 'ALTER SEQUENCE ' || seq_name || ' RESTART WITH 1';
                RAISE NOTICE 'Reset sequence: %', seq_name;
            END LOOP;
        END $$;
        """,
        "",
        "-- Re-enable foreign key checks",
        "SET session_replication_role = DEFAULT;",
        "",
        "-- Verify reset - check table counts",
        "SELECT 'AFTER RESET - Verification:' as info;",
        """
        SELECT 
            t.table_name,
            COALESCE(
                (SELECT COUNT(*) 
                 FROM information_schema.tables t2 
                 WHERE t2.table_name = t.table_name 
                 AND t2.table_schema = 'public'), 0
            ) as table_exists,
            CASE 
                WHEN t.table_name IN (
                    'tenants', 'organizations', 'users', 'companies',
                    'annual_predictions', 'quarterly_predictions', 
                    'bulk_upload_jobs', 'organization_member_whitelists'
                ) THEN 'Application Table'
                ELSE 'Other'
            END as table_type
        FROM information_schema.tables t
        WHERE t.table_schema = 'public' 
        AND t.table_type = 'BASE TABLE'
        ORDER BY table_type, t.table_name;
        """,
        "",
        "SELECT 'Database reset completed successfully!' as result;"
    ]

def main():
    """Main function"""
    print("🗄️ AccuNode Database Reset via Bastion Host")
    print("=" * 50)
    
    # Check if key file exists
    if not os.path.exists(BASTION_KEY):
        print(f"❌ SSH key not found: {BASTION_KEY}")
        print("Make sure you're running from the scripts directory")
        sys.exit(1)
    
    # Get database password
    db_password = input("Enter RDS database password: ").strip()
    if not db_password:
        print("❌ Password is required")
        sys.exit(1)
    
    # Get confirmation
    if not confirm_reset():
        print("❌ Operation cancelled")
        sys.exit(0)
    
    # Generate SQL commands
    logger.info("📝 Generating reset SQL commands...")
    sql_commands = generate_reset_sql()
    
    # Execute reset
    logger.info("🚀 Starting database reset via bastion host...")
    
    success = run_sql_via_bastion(sql_commands, db_password)
    
    if success:
        print("\n🎉 SUCCESS: Database reset completed!")
        print("✅ All application data deleted")
        print("🔄 All sequences reset")
        print("🏗️ Database structure preserved")
        print("\n🚀 You can now run setup_tenant_via_api.py to create fresh data")
    else:
        print("\n❌ Database reset failed. Check logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
