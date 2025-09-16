#!/usr/bin/env python3
"""
Migration script to move from old single-table design to new normalized schema.
This will migrate existing data from companies table to separate prediction tables.
"""

import os
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker
from src.database import Company, AnnualPrediction, QuarterlyPrediction, SessionLocal
from datetime import datetime
import uuid

def migrate_data():
    """Migrate existing data from old companies schema to new normalized schema"""
    
    # Set up database connection
    db = SessionLocal()
    
    try:
        print("🔄 Starting migration from old schema to normalized schema...")
        
        # Get all existing companies with prediction data
        result = db.execute(text("""
            SELECT id, symbol, name, market_cap, sector, reporting_year, reporting_quarter,
                   prediction_type, long_term_debt_to_total_capital, total_debt_to_ebitda,
                   net_income_margin, ebit_to_interest_expense, return_on_assets,
                   sga_margin, return_on_capital, risk_level, confidence, probability,
                   logistic_probability, gbm_probability, predicted_at, created_at, updated_at
            FROM companies 
            WHERE prediction_type IS NOT NULL
        """))
        
        old_companies = result.fetchall()
        print(f"📊 Found {len(old_companies)} companies with prediction data to migrate")
        
        migrated_companies = {}
        annual_predictions_created = 0
        quarterly_predictions_created = 0
        
        for row in old_companies:
            company_id = row.id
            symbol = row.symbol
            prediction_type = row.prediction_type
            
            print(f"\n🏢 Processing {symbol} ({prediction_type})...")
            
            # Create or get clean company record
            if company_id not in migrated_companies:
                # Check if clean company already exists
                clean_company = db.query(Company).filter(
                    Company.symbol == symbol
                ).first()
                
                if not clean_company:
                    # Create new clean company record
                    clean_company = Company(
                        id=company_id,  # Keep same ID
                        symbol=symbol,
                        name=row.name,
                        market_cap=row.market_cap,
                        sector=row.sector,
                        created_at=row.created_at or datetime.utcnow(),
                        updated_at=row.updated_at or datetime.utcnow()
                    )
                    db.add(clean_company)
                    print(f"✅ Created clean company record for {symbol}")
                
                migrated_companies[company_id] = clean_company
            
            # Create appropriate prediction record
            if prediction_type == "annual":
                # Create annual prediction
                annual_pred = AnnualPrediction(
                    company_id=company_id,
                    reporting_year=row.reporting_year or "2024",
                    long_term_debt_to_total_capital=row.long_term_debt_to_total_capital,
                    total_debt_to_ebitda=row.total_debt_to_ebitda,
                    net_income_margin=row.net_income_margin,
                    ebit_to_interest_expense=row.ebit_to_interest_expense,
                    return_on_assets=row.return_on_assets,
                    probability=row.probability,
                    risk_level=row.risk_level,
                    confidence=row.confidence,
                    predicted_at=row.predicted_at or datetime.utcnow(),
                    created_at=row.created_at or datetime.utcnow(),
                    updated_at=row.updated_at or datetime.utcnow()
                )
                db.add(annual_pred)
                annual_predictions_created += 1
                print(f"📅 Created annual prediction for {symbol} - {row.reporting_year}")
                
            elif prediction_type == "quarterly":
                # Create quarterly prediction
                quarterly_pred = QuarterlyPrediction(
                    company_id=company_id,
                    reporting_year=row.reporting_year or "2024",
                    reporting_quarter=row.reporting_quarter or "Q1",
                    total_debt_to_ebitda=row.total_debt_to_ebitda,
                    sga_margin=row.sga_margin,
                    long_term_debt_to_total_capital=row.long_term_debt_to_total_capital,
                    return_on_capital=row.return_on_capital,
                    logistic_probability=row.logistic_probability or row.probability or 0.0,
                    gbm_probability=row.gbm_probability or row.probability or 0.0,
                    ensemble_probability=row.probability or 0.0,
                    risk_level=row.risk_level,
                    confidence=row.confidence,
                    predicted_at=row.predicted_at or datetime.utcnow(),
                    created_at=row.created_at or datetime.utcnow(),
                    updated_at=row.updated_at or datetime.utcnow()
                )
                db.add(quarterly_pred)
                quarterly_predictions_created += 1
                print(f"📈 Created quarterly prediction for {symbol} - {row.reporting_quarter} {row.reporting_year}")
        
        # Commit the new data
        db.commit()
        print(f"\n✅ Migration completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Companies migrated: {len(migrated_companies)}")
        print(f"   - Annual predictions created: {annual_predictions_created}")
        print(f"   - Quarterly predictions created: {quarterly_predictions_created}")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

def drop_old_columns():
    """Drop the old prediction columns from companies table"""
    
    db = SessionLocal()
    
    try:
        print("\n🔄 Dropping old prediction columns from companies table...")
        
        # List of columns to drop
        columns_to_drop = [
            'reporting_year', 'reporting_quarter', 'prediction_type',
            'long_term_debt_to_total_capital', 'total_debt_to_ebitda',
            'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets',
            'sga_margin', 'return_on_capital', 'risk_level', 'confidence',
            'probability', 'logistic_probability', 'gbm_probability', 'predicted_at'
        ]
        
        for column in columns_to_drop:
            try:
                db.execute(text(f"ALTER TABLE companies DROP COLUMN IF EXISTS {column}"))
                print(f"🗑️  Dropped column: {column}")
            except Exception as e:
                print(f"⚠️  Could not drop column {column}: {e}")
        
        db.commit()
        print("✅ Successfully cleaned up companies table")
        
    except Exception as e:
        print(f"❌ Failed to drop old columns: {e}")
        db.rollback()
        
    finally:
        db.close()

if __name__ == "__main__":
    print("🚀 Starting database schema migration...")
    print("This will migrate from old single-table design to new normalized schema")
    
    # Set database URL
    os.environ["DATABASE_URL"] = "postgresql://neondb_owner:npg_2ZLE4VuBytOa@ep-crimson-cell-adrxvu8a-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require"
    
    # Step 1: Migrate data
    if migrate_data():
        print("\n" + "="*50)
        
        # Step 2: Drop old columns
        response = input("Do you want to drop the old columns from companies table? (y/N): ")
        if response.lower() in ['y', 'yes']:
            drop_old_columns()
        else:
            print("⚠️  Old columns kept for safety. You can run this script again to clean them up.")
    
    print("\n🎉 Migration complete!")
