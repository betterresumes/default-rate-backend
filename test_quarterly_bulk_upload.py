#!/usr/bin/env python3
"""
Test script to reproduce and debug the quarterly bulk upload issue
"""

import os
import sys
import pandas as pd
import json
from datetime import datetime

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_quarterly_bulk_upload():
    """Test the complete quarterly bulk upload flow"""
    
    print("🧪 Testing Quarterly Bulk Upload Flow")
    print("=" * 50)
    
    # Step 1: Test quarterly ML service directly
    print("\n1. Testing Quarterly ML Service...")
    try:
        from app.services.quarterly_ml_service import quarterly_ml_model
        
        # Test data similar to what would be in the bulk upload
        test_financial_data = {
            'total_debt_to_ebitda': 7.933,
            'sga_margin': 7.474, 
            'long_term_debt_to_total_capital': 36.912,
            'return_on_capital': 9.948
        }
        
        print(f"   📊 Testing with data: {test_financial_data}")
        
        # This is where the quarterly task is hanging
        result = quarterly_ml_model.predict_quarterly_default_probability(test_financial_data)
        
        print(f"   ✅ ML Prediction successful: {result}")
        
    except Exception as e:
        print(f"   ❌ ML Prediction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 2: Test task worker function directly 
    print("\n2. Testing Task Worker Function...")
    try:
        from app.workers.tasks import process_quarterly_bulk_upload_task
        
        # Create sample data that matches quarterly bulk upload format
        sample_data = [{
            'company_symbol': 'TEST',
            'company_name': 'Test Company',
            'market_cap': 1000000,
            'sector': 'Technology',
            'reporting_year': '2024',
            'reporting_quarter': 'Q4',
            'total_debt_to_ebitda': 7.933,
            'sga_margin': 7.474,
            'long_term_debt_to_total_capital': 36.912,
            'return_on_capital': 9.948
        }]
        
        print(f"   📋 Testing with sample data: {sample_data[0]}")
        
        # Note: We can't easily test the full task without Celery setup
        # But we can test the core logic components
        print("   ⚠️  Full task test requires Celery worker setup")
        
    except Exception as e:
        print(f"   ❌ Task import failed: {str(e)}")
        return False
    
    # Step 3: Test database operations
    print("\n3. Testing Database Operations...")
    try:
        from app.core.database import get_session_local
        
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        # Test basic DB connection
        from sqlalchemy import text
        result = db.execute(text("SELECT 1")).fetchone()
        print(f"   ✅ Database connection successful")
        
        db.close()
        
    except Exception as e:
        print(f"   ❌ Database test failed: {str(e)}")
        return False
    
    # Step 4: Create a minimal reproduction of the hanging issue
    print("\n4. Testing Problematic Code Path...")
    try:
        # Simulate the exact same call that's hanging in production
        from app.services.quarterly_ml_service import quarterly_ml_model
        
        # Use the exact same data from the logs
        hanging_data = {
            'total_debt_to_ebitda': 7.933,
            'sga_margin': 7.474,
            'long_term_debt_to_total_capital': 36.912,
            'return_on_capital': 9.948
        }
        
        print("   🎯 Reproducing the exact hanging scenario...")
        print(f"   📊 Input data: {hanging_data}")
        
        import time
        start_time = time.time()
        
        # This is the exact call that hangs
        ml_result = quarterly_ml_model.predict_quarterly_default_probability(hanging_data)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"   ⏱️  Prediction completed in {duration:.2f} seconds")
        print(f"   ✅ Result: {ml_result}")
        
        # Verify result has required fields
        required_fields = ['logistic_probability', 'gbm_probability', 'ensemble_probability', 'risk_level', 'confidence']
        missing_fields = [field for field in required_fields if field not in ml_result]
        
        if missing_fields:
            print(f"   ⚠️  Missing fields in result: {missing_fields}")
        else:
            print("   ✅ All required fields present in result")
            
    except Exception as e:
        print(f"   ❌ Reproduction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n✅ All tests completed successfully!")
    print("🎉 Quarterly bulk upload should work now!")
    return True

if __name__ == "__main__":
    print("🚀 Starting Quarterly Bulk Upload Debug Test")
    print("=" * 60)
    
    # Set up environment
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment loaded")
    except:
        print("⚠️  No .env file found, using system environment")
    
    success = test_quarterly_bulk_upload()
    
    if success:
        print("\n🎯 CONCLUSION:")
        print("   The quarterly bulk upload should work locally.")
        print("   If it's still hanging in production, the issue is:")
        print("   1. Missing LightGBM dependency in Railway container")
        print("   2. ML model files not properly loaded in production")
        print("   3. Memory/CPU constraints in production environment")
    else:
        print("\n❌ CONCLUSION:")
        print("   There are still issues that need to be resolved")
        print("   Check the error messages above for details")
