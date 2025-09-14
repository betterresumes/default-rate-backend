#!/usr/bin/env python3
"""
Database migration script to convert from 3-table structure to single table
"""
import os
import sys
import asyncio
import asyncpg

# Database configuration - update these if needed
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/default_rate_db")

async def migrate_database():
    print("Starting database migration...")
    
    # Parse the database URL
    if DATABASE_URL.startswith("postgresql://"):
        db_url = DATABASE_URL.replace("postgresql://", "").replace("postgres://", "")
        if "@" in db_url:
            auth, host_db = db_url.split("@", 1)
            if ":" in auth:
                user, password = auth.split(":", 1)
            else:
                user, password = auth, ""
            
            if "/" in host_db:
                host_port, database = host_db.split("/", 1)
            else:
                host_port, database = host_db, "postgres"
            
            if ":" in host_port:
                host, port = host_port.split(":", 1)
                port = int(port)
            else:
                host, port = host_port, 5432
        else:
            # No auth in URL
            host_port_db = db_url
            user, password = "postgres", ""
            if "/" in host_port_db:
                host_port, database = host_port_db.split("/", 1)
            else:
                host_port, database = host_port_db, "postgres"
            
            if ":" in host_port:
                host, port = host_port.split(":", 1)
                port = int(port)
            else:
                host, port = host_port, 5432
    else:
        # Default values
        host, port, user, password, database = "localhost", 5432, "postgres", "password", "default_rate_db"
    
    print(f"Connecting to {host}:{port}/{database} as {user}")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database
        )
        
        print("Connected successfully!")
        
        # First, let's check what tables exist
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        print(f"Existing tables: {[t['table_name'] for t in tables]}")
        
        # Drop old tables if they exist
        print("Dropping old table structure...")
        await conn.execute("DROP TABLE IF EXISTS default_rate_predictions CASCADE")
        await conn.execute("DROP TABLE IF EXISTS financial_ratios CASCADE")
        await conn.execute("DROP TABLE IF EXISTS companies CASCADE")
        
        # Create new companies table with all fields
        print("Creating new companies table...")
        await conn.execute("""
            CREATE TABLE companies (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                
                -- Company Information
                symbol VARCHAR UNIQUE NOT NULL,
                name VARCHAR NOT NULL,
                market_cap NUMERIC(20, 2) NOT NULL,
                sector VARCHAR NOT NULL,
                reporting_year VARCHAR,
                reporting_quarter VARCHAR,
                
                -- Financial Ratios
                long_term_debt_to_total_capital NUMERIC(10, 4) NOT NULL,
                total_debt_to_ebitda NUMERIC(10, 4) NOT NULL,
                net_income_margin NUMERIC(10, 4) NOT NULL,
                ebit_to_interest_expense NUMERIC(10, 4) NOT NULL,
                return_on_assets NUMERIC(10, 4) NOT NULL,
                
                -- Prediction Results
                risk_level VARCHAR NOT NULL,
                confidence NUMERIC(5, 4) NOT NULL,
                probability NUMERIC(5, 4),
                predicted_at TIMESTAMP DEFAULT NOW(),
                
                -- Timestamps
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        
        # Create index on symbol for faster lookups
        await conn.execute("CREATE INDEX idx_companies_symbol ON companies(symbol)")
        
        print("Migration completed successfully!")
        print("New schema:")
        print("- Single 'companies' table with all company info, financial ratios, and predictions")
        print("- Simplified data model with no foreign key relationships")
        
        await conn.close()
        
    except Exception as e:
        print(f"Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(migrate_database())
    if success:
        print("\n✅ Database migration completed successfully!")
        print("You can now test the new endpoints.")
    else:
        print("\n❌ Database migration failed!")
        sys.exit(1)
