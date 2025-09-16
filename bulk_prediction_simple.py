#!/usr/bin/env python3
"""
Bulk Prediction Script - Simple Version
Loads stock data from step files and runs predictions for the first 100 stocks,
saving results to the database.
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to Python path to enable proper imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Now we can import the src module as a package
from src.database import get_db, Company, User, AnnualPrediction, SessionLocal
from src.services import CompanyService
from src.ml_service import MLModelService

def load_annual_data():
    """Load annual step data"""
    print("Loading annual step data...")
    
    annual_step_path = os.path.join('src', 'models', 'annual_step.pkl')
    
    with open(annual_step_path, 'rb') as f:
        annual_data = pickle.load(f)
    
    print(f"Loaded annual data: {annual_data.shape}")
    
    return annual_data

def get_or_create_test_user(db):
    """Get or create a test user for predictions"""
    test_email = "test@bulkprediction.com"
    user = db.query(User).filter(User.email == test_email).first()
    
    if not user:
        user = User(
            email=test_email,
            username="bulk_prediction_user",
            hashed_password="dummy_hash",  # Not used for this script
            full_name="Bulk Prediction Test User",
            is_active=True,
            is_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created test user: {user.email}")
    else:
        print(f"Using existing test user: {user.email}")
    
    return user

def create_company_from_data(row, company_service):
    """Create or get company from step data row"""
    # Extract company information
    symbol = str(row.get('ticker', '')).strip()
    name = str(row.get('company name', '')).strip()
    
    if not symbol and not name:
        return None
    
    # Use symbol as fallback if missing
    if not symbol:
        symbol = name[:10].replace(' ', '').upper()
    if not name:
        name = symbol
    
    # Set market cap to $100 million as specified
    market_cap = 100000.0  # $100 million in thousands
    
    # Use Industry as sector
    sector = str(row.get('Industry', 'Unknown')).strip() or 'Unknown'
    
    try:
        company = company_service.create_or_get_company(
            symbol=symbol,
            name=name,
            market_cap=market_cap,
            sector=sector
        )
        return company
    except Exception as e:
        print(f"Error creating company {symbol}/{name}: {e}")
        return None

def prepare_annual_ratios(row):
    """Extract and prepare ratios for annual prediction"""
    return {
        'long_term_debt_to_total_capital': safe_float(row.get('long-term debt / total capital (%)')),
        'total_debt_to_ebitda': safe_float(row.get('total debt / ebitda')),
        'net_income_margin': safe_float(row.get('net income margin')),
        'ebit_to_interest_expense': safe_float(row.get('ebit / interest expense')),
        'return_on_assets': safe_float(row.get('return on assets'))
    }

def safe_float(value):
    """Safely convert value to float, handling NM, NaN, and missing values"""
    if value is None or pd.isna(value):
        return 0.0
    
    # Handle "NM" (Not Meaningful) values
    if isinstance(value, str) and value.strip().upper() == 'NM':
        return 0.0
        
    try:
        float_val = float(value)
        if np.isnan(float_val) or np.isinf(float_val):
            return 0.0
        return float_val
    except (ValueError, TypeError):
        return 0.0

def run_annual_prediction(company, ratios, ml_service, company_service, fiscal_year):
    """Run annual prediction for a company"""
    try:
        # Use fiscal year from data, default to 2024 if not available
        year = str(int(fiscal_year)) if fiscal_year and not pd.isna(fiscal_year) else "2024"
        quarter = "Q4"  # Default quarter as specified
        
        # Run prediction
        prediction_result = ml_service.predict_default_probability(ratios)
        
        if 'error' in prediction_result:
            print(f"❌ Prediction error for {company.symbol}: {prediction_result['error']}")
            return None
        
        # Create prediction record using the correct signature
        annual_prediction = company_service.create_annual_prediction(
            company=company,
            financial_data=ratios,
            prediction_results=prediction_result,
            reporting_year=year,
            reporting_quarter=quarter
        )
        
        print(f"✅ Annual prediction created for {company.symbol} (FY {year}): {prediction_result['probability']:.4f}")
        return annual_prediction
        
    except Exception as e:
        print(f"❌ Error creating annual prediction for {company.symbol}: {e}")
        return None

def main():
    """Main function to run bulk predictions"""
    print("🚀 Starting bulk prediction script for ANNUAL data only...")
    
    # Load step data
    annual_data = load_annual_data()
    
    # Initialize ML services
    print("Loading ML models...")
    ml_service = MLModelService()
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Get or create test user
        user = get_or_create_test_user(db)
        company_service = CompanyService(db)
        
        # Limit to first 100 records for testing
        NUM_RECORDS = 100
        print(f"Processing first {NUM_RECORDS} annual records...")
        
        annual_success = 0
        annual_errors = 0
        
        # Process annual predictions only
        print("\n📊 Processing Annual Predictions...")
        for i, (_, row) in enumerate(annual_data.head(NUM_RECORDS).iterrows()):
            if i % 10 == 0:
                print(f"Progress: {i}/{NUM_RECORDS}")
            
            # Create or get company
            company = create_company_from_data(row, company_service)
            if not company:
                print(f"❌ Skipping row {i+1}: Could not create/get company")
                annual_errors += 1
                continue
            
            # Prepare ratios
            ratios = prepare_annual_ratios(row)
            
            # Check if we have valid data
            if all(v == 0.0 for v in ratios.values()):
                print(f"❌ Skipping {company.symbol}: No valid financial data")
                annual_errors += 1
                continue
            
            # Get fiscal year from data
            fiscal_year = row.get('fy')
            
            # Run prediction
            prediction = run_annual_prediction(
                company, ratios, ml_service, company_service, fiscal_year
            )
            
            if prediction:
                annual_success += 1
            else:
                annual_errors += 1
        
        print(f"\n✅ Bulk prediction completed!")
        print(f"Annual predictions created: {annual_success}/{NUM_RECORDS}")
        print(f"Errors/Skipped: {annual_errors}/{NUM_RECORDS}")
        print(f"Success rate: {annual_success/(NUM_RECORDS)*100:.1f}%")
        
    except Exception as e:
        print(f"❌ Error in bulk prediction: {e}")
        db.rollback()
        raise
    
    finally:
        db.close()

if __name__ == "__main__":
    main()
