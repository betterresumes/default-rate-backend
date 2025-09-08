#!/usr/bin/env python3
"""
Database schema update script
Drops existing tables and recreates them with the new schema
"""

import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database import create_database_engine, Base
from sqlalchemy import text

def reset_database():
    """Drop all tables and recreate them"""
    print("🗄️ Resetting database schema...")
    
    try:
        engine = create_database_engine()
        
        # Drop all tables
        print("🗑️ Dropping existing tables...")
        with engine.connect() as conn:
            # Drop tables in correct order (handle foreign key constraints)
            conn.execute(text("DROP TABLE IF EXISTS default_rate_predictions CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS financial_ratios CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS companies CASCADE"))
            conn.execute(text("DROP TABLE IF EXISTS sectors CASCADE"))
            conn.commit()
        
        print("✅ Existing tables dropped successfully!")
        
        # Create all tables with new schema
        print("📊 Creating tables with new schema...")
        Base.metadata.create_all(bind=engine)
        print("✅ New tables created successfully!")
        
        print("\n🎉 Database schema updated successfully!")
        print("✨ New columns added:")
        print("   - financial_ratios.fixed_asset_turnover")
        print("   - financial_ratios.total_debt_ebitda")
        print("   - default_rate_predictions.fixed_asset_turnover")
        print("   - default_rate_predictions.total_debt_ebitda")
        
        return True
        
    except Exception as e:
        print(f"❌ Database reset failed: {e}")
        return False

if __name__ == "__main__":
    reset_database()
