#!/usr/bin/env python3
"""
Test script to isolate the quarterly ML prediction issue
"""

import os
import sys
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_quarterly_ml_service():
    """Test the quarterly ML service directly"""
    try:
        print("🔄 Testing quarterly ML service...")
        from app.services.quarterly_ml_service import quarterly_ml_model
        
        # Test data that matches what the task is trying to process
        financial_data = {
            'total_debt_to_ebitda': 7.933,
            'sga_margin': 7.474,
            'long_term_debt_to_total_capital': 36.912,
            'return_on_capital': 9.948
        }
        
        print(f"📊 Input data: {financial_data}")
        
        print("🤖 Calling quarterly ML prediction...")
        start_time = datetime.now()
        
        # This is the exact call that's hanging in the task
        ml_result = quarterly_ml_model.predict_quarterly_default_probability(financial_data)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Prediction completed in {duration:.2f} seconds")
        print(f"📈 Result: {ml_result}")
        
        return ml_result
        
    except Exception as e:
        print(f"❌ Error in quarterly ML service: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_annual_ml_service_comparison():
    """Test the annual ML service for comparison"""
    try:
        print("\n🔄 Testing annual ML service for comparison...")
        from app.services.ml_service import ml_model
        
        # Test data similar to annual format
        financial_data = {
            'long_term_debt_to_total_capital': 36.912,
            'total_debt_to_ebitda': 7.933,
            'net_income_margin': 5.2,  # Example value
            'ebit_to_interest_expense': 8.1,  # Example value
            'return_on_assets': 3.5   # Example value
        }
        
        print(f"📊 Annual input data: {financial_data}")
        
        print("🤖 Calling annual ML prediction...")
        start_time = datetime.now()
        
        ml_result = ml_model.predict_default_probability(financial_data)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"✅ Annual prediction completed in {duration:.2f} seconds")
        print(f"📈 Annual result: {ml_result}")
        
        return ml_result
        
    except Exception as e:
        print(f"❌ Error in annual ML service: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_model_loading():
    """Test if models load correctly"""
    try:
        print("\n🔄 Testing model loading...")
        
        # Test quarterly models
        from app.services.quarterly_ml_service import QuarterlyMLModelService
        quarterly_service = QuarterlyMLModelService()
        print(f"✅ Quarterly models loaded: logistic={quarterly_service.logistic_model is not None}, gbm={quarterly_service.gbm_model is not None}")
        
        # Test annual models  
        from app.services.ml_service import MLModelService
        annual_service = MLModelService()
        print(f"✅ Annual models loaded successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading models: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Testing ML Services Locally")
    print("=" * 50)
    
    # Test 1: Model loading
    if not test_model_loading():
        print("❌ Model loading failed - stopping tests")
        sys.exit(1)
    
    # Test 2: Annual ML service (working one)
    annual_result = test_annual_ml_service_comparison()
    
    # Test 3: Quarterly ML service (problematic one)
    quarterly_result = test_quarterly_ml_service()
    
    print("\n" + "=" * 50)
    if quarterly_result:
        print("✅ All tests passed! Quarterly ML service is working locally.")
    else:
        print("❌ Quarterly ML service failed locally - this is the source of the hang!")
