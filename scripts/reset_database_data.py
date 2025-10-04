#!/usr/bin/env python3
"""
Database Reset Script
Usage: python scripts/reset_database_data.py
Warning: This will delete ALL data from the database while preserving structure
"""

import os
import psycopg2
from psycopg2 import sql
import logging
from typing import List
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database configuration - Update these with your RDS details
DB_CONFIG = {
    "host": "accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com",
    "port": "5432",
    "database": "postgres",
    "user": "accunode_admin",
    "password": "YOUR_RDS_PASSWORD_HERE"  # Replace with actual password
}

def get_all_tables(cursor) -> List[str]:
    """Get all user-defined tables (excluding system tables)"""
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)
    return [row[0] for row in cursor.fetchall()]

def get_table_dependencies(cursor) -> List[str]:
    """Get tables in dependency order (tables with foreign keys last)"""
    cursor.execute("""
        WITH RECURSIVE table_deps AS (
            -- Base tables (no dependencies)
            SELECT 
                t.table_name,
                0 as level
            FROM information_schema.tables t
            WHERE t.table_schema = 'public' 
            AND t.table_type = 'BASE TABLE'
            AND t.table_name NOT IN (
                SELECT DISTINCT tc.table_name
                FROM information_schema.table_constraints tc
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
            )
            
            UNION ALL
            
            -- Tables with dependencies
            SELECT 
                t.table_name,
                td.level + 1
            FROM information_schema.tables t
            JOIN information_schema.table_constraints tc ON t.table_name = tc.table_name
            JOIN table_deps td ON 1=1
            WHERE t.table_schema = 'public' 
            AND t.table_type = 'BASE TABLE'
            AND tc.constraint_type = 'FOREIGN KEY'
            AND t.table_name NOT IN (SELECT table_name FROM table_deps)
        )
        SELECT DISTINCT table_name 
        FROM table_deps 
        ORDER BY level DESC, table_name;
    """)
    return [row[0] for row in cursor.fetchall()]

def disable_foreign_key_checks(cursor):
    """Disable foreign key constraints temporarily"""
    logger.info("🔒 Disabling foreign key constraints...")
    cursor.execute("SET session_replication_role = replica;")

def enable_foreign_key_checks(cursor):
    """Re-enable foreign key constraints"""
    logger.info("🔓 Re-enabling foreign key constraints...")
    cursor.execute("SET session_replication_role = DEFAULT;")

def truncate_table(cursor, table_name: str):
    """Truncate a single table"""
    try:
        # Use TRUNCATE CASCADE to handle foreign key dependencies
        cursor.execute(sql.SQL("TRUNCATE TABLE {} RESTART IDENTITY CASCADE").format(
            sql.Identifier(table_name)
        ))
        logger.info(f"✅ Truncated table: {table_name}")
    except Exception as e:
        logger.error(f"❌ Failed to truncate {table_name}: {e}")
        raise

def reset_sequences(cursor):
    """Reset all sequences to start from 1"""
    logger.info("🔄 Resetting sequences...")
    
    # Get all sequences
    cursor.execute("""
        SELECT sequence_name 
        FROM information_schema.sequences 
        WHERE sequence_schema = 'public';
    """)
    
    sequences = [row[0] for row in cursor.fetchall()]
    
    for sequence in sequences:
        try:
            cursor.execute(sql.SQL("ALTER SEQUENCE {} RESTART WITH 1").format(
                sql.Identifier(sequence)
            ))
            logger.info(f"✅ Reset sequence: {sequence}")
        except Exception as e:
            logger.warning(f"⚠️ Could not reset sequence {sequence}: {e}")

def get_table_counts(cursor) -> dict:
    """Get row counts for all tables"""
    tables = get_all_tables(cursor)
    counts = {}
    
    for table in tables:
        try:
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(
                sql.Identifier(table)
            ))
            counts[table] = cursor.fetchone()[0]
        except Exception as e:
            counts[table] = f"Error: {e}"
    
    return counts

def confirm_reset() -> bool:
    """Ask user for confirmation before proceeding"""
    print("\n" + "=" * 60)
    print("⚠️  DATABASE RESET WARNING")
    print("=" * 60)
    print("This operation will:")
    print("✗ DELETE ALL DATA from all tables")
    print("✗ RESET all sequences to start from 1")
    print("✗ Cannot be undone")
    print("\nThis operation will NOT:")
    print("✓ Delete tables or database structure")
    print("✓ Delete indexes or constraints")
    print("✓ Delete stored procedures or functions")
    print("=" * 60)
    
    response = input("\nType 'YES DELETE ALL DATA' to confirm: ").strip()
    return response == 'YES DELETE ALL DATA'

def main():
    """Main function to reset database data"""
    print("🗄️ AccuNode Database Reset Tool")
    print("=" * 50)
    
    # Check if password is set
    if DB_CONFIG["password"] == "YOUR_RDS_PASSWORD_HERE":
        print("❌ Please update the DB_CONFIG password in the script before running.")
        sys.exit(1)
    
    # Get user confirmation
    if not confirm_reset():
        print("❌ Operation cancelled by user.")
        sys.exit(0)
    
    try:
        # Connect to database
        logger.info("🔌 Connecting to database...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = False
        cursor = conn.cursor()
        
        # Get initial table counts
        logger.info("📊 Getting current table counts...")
        initial_counts = get_table_counts(cursor)
        
        print(f"\n📊 CURRENT DATABASE STATE:")
        total_rows = 0
        for table, count in initial_counts.items():
            if isinstance(count, int):
                print(f"   {table}: {count:,} rows")
                total_rows += count
            else:
                print(f"   {table}: {count}")
        print(f"   TOTAL ROWS: {total_rows:,}")
        
        if total_rows == 0:
            print("ℹ️ Database is already empty. Nothing to reset.")
            return
        
        # Start transaction
        logger.info("🚀 Starting database reset...")
        
        # Disable foreign key constraints
        disable_foreign_key_checks(cursor)
        
        # Get all tables
        tables = get_all_tables(cursor)
        logger.info(f"📋 Found {len(tables)} tables to reset")
        
        # Truncate all tables
        logger.info("🗑️ Truncating all tables...")
        for table in tables:
            truncate_table(cursor, table)
        
        # Reset sequences
        reset_sequences(cursor)
        
        # Re-enable foreign key constraints
        enable_foreign_key_checks(cursor)
        
        # Commit transaction
        conn.commit()
        
        # Verify reset
        logger.info("✅ Verifying database reset...")
        final_counts = get_table_counts(cursor)
        
        print(f"\n📊 DATABASE STATE AFTER RESET:")
        total_rows_after = 0
        for table, count in final_counts.items():
            if isinstance(count, int):
                print(f"   {table}: {count:,} rows")
                total_rows_after += count
            else:
                print(f"   {table}: {count}")
        print(f"   TOTAL ROWS: {total_rows_after:,}")
        
        if total_rows_after == 0:
            logger.info("🎉 Database reset completed successfully!")
            print("\n✅ SUCCESS: All data has been removed from the database.")
            print("🔄 All sequences have been reset to start from 1.")
            print("🏗️ Database structure preserved (tables, indexes, constraints).")
        else:
            logger.warning(f"⚠️ Warning: {total_rows_after} rows still remain in database.")
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
        
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        logger.info("🔌 Database connection closed.")

if __name__ == "__main__":
    main()
