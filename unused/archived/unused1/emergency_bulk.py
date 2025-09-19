#!/usr/bin/env python3
"""
Emergency Ultra-Fast Bulk Processor
Simplified version to get predictions working immediately.
"""

import os
import sys
import pickle
import pandas as pd
import numpy as np
import time
from datetime import datetime
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

from src.database import SessionLocal, Company, User, AnnualPrediction
from src.services import CompanyService
from src.ml_service import MLModelService

def emergency_bulk_process():
    """Emergency processing - get predictions created ASAP"""
    print("🚨 EMERGENCY BULK PROCESSOR")
    print("=" * 50)
    
    try:
        # Initialize ML service
        print("🔧 Initializing ML service...")
        ml_service = MLModelService()
        print("✅ ML service ready")
        
        # Load data
        print("📁 Loading data...")
        annual_step_path = os.path.join('src', 'models', 'annual_step.pkl')
        with open(annual_step_path, 'rb') as f:
            data = pickle.load(f)
        print(f"✅ Loaded {len(data):,} records")
        
        # Quick preprocessing
        print("🔍 Quick preprocessing...")
        data = data[data['ticker'].notna() & (data['ticker'] != '')].copy()
        data['ticker'] = data['ticker'].astype(str).str.upper()
        print(f"✅ {len(data):,} valid records")
        
        # Database setup
        print("🗄️  Setting up database...")
        db = SessionLocal()
        
        # Get or create user
        test_email = "emergency_bulk@predictions.com"
        user = db.query(User).filter(User.email == test_email).first()
        if not user:
            user = User(
                email=test_email,
                username="emergency_bulk",
                hashed_password="dummy",
                full_name="Emergency Bulk Processor",
                is_active=True,
                is_verified=True,
                role="system"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        print(f"✅ User ready: {user.email}")
        
        # Process small batch for testing
        print("🚀 Processing sample batch...")
        company_service = CompanyService(db)
        
        # Take first 50 records for emergency test
        sample_data = data.head(50)
        successful = 0
        failed = 0
        
        for idx, (_, row) in enumerate(sample_data.iterrows()):
            try:
                print(f"📝 Processing record {idx+1}/50: {row['ticker']}")
                
                # Extract financial ratios
                ratios = {
                    'long_term_debt_to_total_capital': safe_float(row.get('long-term debt / total capital (%)')),
                    'total_debt_to_ebitda': safe_float(row.get('total debt / ebitda')),
                    'net_income_margin': safe_float(row.get('net income margin')),
                    'ebit_to_interest_expense': safe_float(row.get('ebit / interest expense')),
                    'return_on_assets': safe_float(row.get('return on assets'))
                }
                
                # Create company
                ticker = str(row['ticker']).strip().upper()
                company_name = str(row.get('company name', ticker))
                
                company = company_service.create_or_get_company(
                    symbol=ticker,
                    name=company_name,
                    market_cap=100000.0,
                    sector="Other"
                )
                
                if not company:
                    print(f"  ❌ Failed to create company for {ticker}")
                    failed += 1
                    continue
                
                print(f"  ✅ Company created/found: {company.symbol} (ID: {company.id})")
                
                # Run ML prediction
                prediction_result = ml_service.predict_default_probability(ratios)
                
                if 'error' in prediction_result:
                    print(f"  ❌ ML prediction failed: {prediction_result['error']}")
                    failed += 1
                    continue
                
                print(f"  🧠 ML prediction: probability={prediction_result['probability']:.3f}")
                
                # Create annual prediction DIRECTLY
                fiscal_year = row.get('fy', 2024)
                reporting_year = str(int(fiscal_year)) if not pd.isna(fiscal_year) else "2024"
                
                annual_prediction = AnnualPrediction(
                    company_id=company.id,
                    user_id=user.id,
                    reporting_year=reporting_year,
                    reporting_quarter="Q4",
                    long_term_debt_to_total_capital=ratios['long_term_debt_to_total_capital'],
                    total_debt_to_ebitda=ratios['total_debt_to_ebitda'],
                    net_income_margin=ratios['net_income_margin'],
                    ebit_to_interest_expense=ratios['ebit_to_interest_expense'],
                    return_on_assets=ratios['return_on_assets'],
                    probability=prediction_result['probability'],
                    risk_score=prediction_result.get('risk_level', 'MEDIUM'),
                    model_version=prediction_result.get('model_version', '1.0')
                )
                
                db.add(annual_prediction)
                db.commit()
                db.refresh(annual_prediction)
                
                print(f"  💾 Prediction saved! ID: {annual_prediction.id}")
                successful += 1
                
            except Exception as e:
                print(f"  💥 Error processing {row.get('ticker', 'unknown')}: {e}")
                failed += 1
                db.rollback()
                continue
        
        print("=" * 50)
        print(f"🏁 EMERGENCY BATCH COMPLETE")
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Success rate: {(successful/(successful+failed)*100):.1f}%")
        
        if successful > 0:
            print(f"🎉 SUCCESS! {successful} predictions created in database!")
            print(f"💡 System is working - ready for full run")
        else:
            print(f"💥 FAILED! No predictions created - needs debugging")
        
        db.close()
        
    except Exception as e:
        print(f"💥 CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

def safe_float(value) -> Optional[float]:
    """Safe float conversion"""
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str) and value.strip().upper() in ['NM', 'N/A', 'NA', '', '-']:
        return None
    try:
        float_val = float(value)
        return None if (np.isnan(float_val) or np.isinf(float_val)) else float_val
    except:
        return None

if __name__ == "__main__":
    emergency_bulk_process()
