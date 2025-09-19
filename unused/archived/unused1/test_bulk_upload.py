#!/usr/bin/env python3
"""
Test the first Excel file with the bulk-upload-async endpoint
"""

import requests
import os
from pathlib import Path

#!/usr/bin/env python3
"""
Test the bulk-upload-async endpoint with the first Excel file
"""

import requests
import time

def test_bulk_upload():
    """Test the bulk upload endpoint with authentication"""
    
    # Your JWT token
    token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2ZDE3NTJiNy1hZDQxLTRkYjgtOTk4ZS02ZWVhYmNiZmE3NjQiLCJleHAiOjE3NTgxMTk1NjN9.Pcm3LduujNIeSJMKV0OhmlHPwkbHgdGyaccONjOPoos"
    
    # Check if files exist
    file_path = Path('bulk_upload_files/annual_predictions_part_1.xlsx')
    if not file_path.exists():
        print("❌ File not found: bulk_upload_files/annual_predictions_part_1.xlsx")
        print("Please run convert_to_excel.py first")
        return False
    
    print("🧪 Testing bulk-upload-async endpoint with first Excel file...")
    print(f"📄 File: {file_path}")
    print(f"📊 File size: {file_path.stat().st_size / 1024:.1f} KB")
    
    # API endpoint
    base_url = "http://localhost:8000"  # Adjust if your server runs on different port
    endpoint = f"{base_url}/api/predictions/bulk-predict-async"
    
    # Check if server is running
    try:
        health_response = requests.get(f"{base_url}/health", timeout=5)
        if health_response.status_code != 200:
            print("❌ Server health check failed")
            return False
        print("✅ Server is running")
    except requests.exceptions.RequestException as e:
        print("❌ Server is not running. Please start it with:")
        print("   uvicorn src.app:app --reload")
        return False
    
    # Prepare the request
    files = {
        'file': ('annual_predictions_part_1.xlsx', open(file_path, 'rb'), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    }
    
    data = {
        'prediction_type': 'annual'
    }
    
    # You'll need to add authentication if required
    # For testing, you might need to get a token first
    headers = {
        # 'Authorization': 'Bearer YOUR_TOKEN_HERE'  # Add if authentication is required
    }
    
    try:
        print("🚀 Sending request to bulk-upload-async endpoint...")
        
        response = requests.post(
            endpoint,
            files=files,
            data=data,
            headers=headers,
            timeout=30  # 30 second timeout
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS! Bulk upload accepted")
            print(f"📋 Response: {result}")
            
            if 'job_id' in result:
                print(f"🆔 Job ID: {result['job_id']}")
                print("💡 You can check job status with this ID")
            
            return True
            
        elif response.status_code == 422:
            print("❌ Validation Error (422)")
            try:
                error_details = response.json()
                print(f"📋 Error Details: {error_details}")
            except:
                print(f"📋 Response Text: {response.text}")
            return False
            
        elif response.status_code == 401:
            print("❌ Authentication required (401)")
            print("💡 You need to login first or provide a valid token")
            return False
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            print(f"📋 Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    finally:
        files['file'][1].close()

def verify_file_format():
    """Verify the file format before testing"""
    print("🔍 VERIFYING FILE FORMAT...")
    
    import pandas as pd
    
    file_path = Path('bulk_upload_files/annual_predictions_part_1.xlsx')
    
    try:
        df = pd.read_excel(file_path)
        
        required_columns = [
            'stock_symbol', 'company_name', 'long_term_debt_to_total_capital',
            'total_debt_to_ebitda', 'net_income_margin', 'ebit_to_interest_expense', 'return_on_assets'
        ]
        
        print(f"📊 Total records: {len(df)}")
        print(f"📋 Columns: {list(df.columns)}")
        
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            print(f"❌ Missing required columns: {missing_cols}")
            return False
        else:
            print("✅ All required columns present")
        
        # Show sample data
        print("\n🔍 SAMPLE DATA (first 3 rows):")
        pd.set_option('display.max_columns', None)
        pd.set_option('display.width', None)
        sample_cols = ['stock_symbol', 'company_name', 'market_cap', 'sector', 'reporting_year']
        print(df[sample_cols].head(3))
        
        # Check for nulls in critical fields
        null_symbols = df['stock_symbol'].isna().sum()
        null_names = df['company_name'].isna().sum()
        
        if null_symbols > 0 or null_names > 0:
            print(f"⚠️ Found nulls: symbols={null_symbols}, names={null_names}")
        else:
            print("✅ No nulls in critical fields")
        
        return True
        
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 BULK UPLOAD ENDPOINT TESTER")
    print("=" * 50)
    
    # First verify file format
    if not verify_file_format():
        print("💥 File format verification failed")
        return
    
    print("\n" + "=" * 50)
    
    # Test the endpoint
    success = test_bulk_upload()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TEST PASSED! The Excel file format is correct")
        print("✅ You can now upload all 4 files using the endpoint")
        print("\n📋 Next steps:")
        print("1. Upload part_1.xlsx (tested ✅)")
        print("2. Wait 30 seconds")
        print("3. Upload part_2.xlsx")
        print("4. Wait 30 seconds")
        print("5. Upload part_3.xlsx")
        print("6. Wait 30 seconds")
        print("7. Upload part_4.xlsx")
    else:
        print("💥 TEST FAILED! Check the error messages above")
        print("🔧 Fix the issues and try again")

if __name__ == "__main__":
    main()
