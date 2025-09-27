#!/usr/bin/env python3
"""
Database Migration Script: Convert market_cap to millions of dollars
Convert from raw dollar values to millions for better storage and readability

Examples:
- $2.78 Trillion → 2,782,905 millions
- $1.16 Trillion → 1,164,331 millions  
- $100 Million → 100 millions
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import get_database_url

def convert_market_cap_to_millions():
    """Convert market_cap from raw dollars to millions of dollars"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        print("🔄 Converting market_cap to millions of dollars...")
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # First, check current data
                check_sql = """
                SELECT symbol, name, market_cap 
                FROM companies 
                ORDER BY market_cap DESC 
                LIMIT 5;
                """
                current_data = conn.execute(text(check_sql)).fetchall()
                
                if current_data:
                    print("📊 Current largest market caps (before conversion):")
                    for row in current_data:
                        print(f"   {row[0]}: ${row[2]:,.0f}")
                
                # Convert existing values from dollars to millions of dollars
                # Divide by 1,000,000 to convert to millions
                update_sql = """
                UPDATE companies 
                SET market_cap = ROUND(market_cap / 1000000.0, 2)
                WHERE market_cap > 1000000;
                """
                
                result = conn.execute(text(update_sql))
                print(f"✅ Updated {result.rowcount} companies with market cap conversion")
                
                # Now alter the column to use more appropriate precision
                # Precision 15, scale 2 can handle up to 10^13 millions (10^19 dollars)
                alter_sql = """
                ALTER TABLE companies 
                ALTER COLUMN market_cap TYPE NUMERIC(15,2);
                """
                
                conn.execute(text(alter_sql))
                
                # Add a comment to the column for clarity
                comment_sql = """
                COMMENT ON COLUMN companies.market_cap IS 'Market capitalization in millions of US dollars';
                """
                
                conn.execute(text(comment_sql))
                
                trans.commit()
                
                print("✅ Successfully converted market_cap to millions of dollars")
                print("🎯 Column precision updated to (15,2) for millions")
                
                # Test the conversion
                test_sql = """
                SELECT symbol, name, market_cap 
                FROM companies 
                ORDER BY market_cap DESC 
                LIMIT 5;
                """
                
                converted_data = conn.execute(text(test_sql)).fetchall()
                if converted_data:
                    print("📊 Converted market caps (in millions):")
                    for row in converted_data:
                        print(f"   {row[0]}: ${row[2]:,.2f}M (${row[2]*1000000:,.0f})")
                
                # Verify column info
                column_info_sql = """
                SELECT column_name, data_type, numeric_precision, numeric_scale
                FROM information_schema.columns 
                WHERE table_name = 'companies' AND column_name = 'market_cap';
                """
                
                result = conn.execute(text(column_info_sql)).fetchone()
                if result:
                    print(f"� Updated column info: {result[0]} - {result[1]}({result[2]},{result[3]})")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting market cap conversion to millions...")
    load_dotenv()
    
    if convert_market_cap_to_millions():
        print("✅ Conversion completed successfully!")
        print("💡 Market cap values are now stored in millions of dollars")
        print("💡 Update your data generation and processing logic accordingly")
    else:
        print("❌ Conversion failed!")
        sys.exit(1)
