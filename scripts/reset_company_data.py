#!/usr/bin/env python3
"""
Clear existing company data and regenerate with proper market cap values
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import get_database_url

def reset_company_data():
    """Clear existing company data that has incorrect market cap values"""
    try:
        # Get database connection
        database_url = get_database_url()
        engine = create_engine(database_url)
        
        print("🔄 Resetting company data with correct market cap values...")
        
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Delete existing predictions first (due to foreign key constraints)
                print("📝 Clearing existing prediction data...")
                conn.execute(text("DELETE FROM quarterly_predictions;"))
                conn.execute(text("DELETE FROM annual_predictions;"))
                
                # Delete existing companies
                print("📝 Clearing existing company data...")
                conn.execute(text("DELETE FROM companies;"))
                
                trans.commit()
                
                print("✅ Successfully cleared existing data")
                print("💡 Now you can upload new data with correct market cap values in millions")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"❌ Reset failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting company data reset...")
    load_dotenv()
    
    if reset_company_data():
        print("✅ Reset completed successfully!")
        print("🎯 Ready for new uploads with market cap in millions")
    else:
        print("❌ Reset failed!")
        sys.exit(1)
