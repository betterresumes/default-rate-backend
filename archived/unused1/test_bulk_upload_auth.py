#!/usr/bin/env python3
"""
Test bulk upload with authentication
"""

import requests
import json
from pathlib import Path

def create_test_user_and_login():
    """Create a test user and login to get token"""
    base_url = "http://localhost:8000"
    
    # Test user credentials
    test_user = {
        "email": "test@bulkupload.com",
        "username": "bulktest",
        "password": "testpassword123",
        "full_name": "Bulk Upload Tester"
    }
    
    print("👤 Creating test user...")
    
    # Try to register user
    try:
        register_response = requests.post(
            f"{base_url}/api/auth/register",
            json=test_user,
            timeout=10
        )
        
        if register_response.status_code == 201:
            print("✅ Test user created successfully")
        elif register_response.status_code == 400:
            # User might already exist
            print("ℹ️ Test user already exists")
        else:
            print(f"⚠️ Register response: {register_response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Registration error: {e}")
    
    # Login to get token
    print("🔐 Logging in...")
    
    login_data = {
        "email": "patil@gmail.com",
        "password": "Test123*"
    }
    
    try:
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,  # JSON data for Pydantic model
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data["access_token"]
            print("✅ Login successful")
            return access_token
        else:
            print(f"❌ Login failed: {login_response.status_code}")
            print(f"Response: {login_response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def test_bulk_upload_with_auth():
    """Test bulk upload with authentication"""
    
    # Get authentication token
    token = create_test_user_and_login()
    if not token:
        print("💥 Could not get authentication token")
        return False
    
    print(f"🔑 Got access token: {token[:20]}...")
    
    # Test the bulk upload
    file_path = Path('bulk_upload_files/annual_predictions_part_1.xlsx')
    if not file_path.exists():
        print("❌ File not found")
        return False
    
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/predictions/bulk-predict-async"
    
    # Prepare the request
    files = {
        'file': ('annual_predictions_part_1.xlsx', open(file_path, 'rb'), 
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    }
    
    data = {
        'prediction_type': 'annual'
    }
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    try:
        print("🚀 Testing bulk upload with authentication...")
        
        response = requests.post(
            endpoint,
            files=files,
            data=data,
            headers=headers,
            timeout=60  # Longer timeout for bulk processing
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("🎉 SUCCESS! Bulk upload accepted")
            print(f"📋 Response: {json.dumps(result, indent=2)}")
            
            if 'job_id' in result:
                print(f"🆔 Job ID: {result['job_id']}")
                print("💡 You can check job status with this ID")
                
                # Test job status check
                job_id = result['job_id']
                check_job_status(job_id, token)
            
            return True
            
        else:
            print(f"❌ Request failed with status {response.status_code}")
            try:
                error_details = response.json()
                print(f"📋 Error Details: {json.dumps(error_details, indent=2)}")
            except:
                print(f"📋 Response Text: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False
    finally:
        files['file'][1].close()

def check_job_status(job_id, token):
    """Check the status of the bulk upload job"""
    base_url = "http://localhost:8000"
    status_endpoint = f"{base_url}/api/predictions/bulk-job-status/{job_id}"
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    try:
        print(f"📊 Checking job status for {job_id}...")
        
        response = requests.get(status_endpoint, headers=headers, timeout=10)
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"📋 Job Status: {json.dumps(status_data, indent=2)}")
        else:
            print(f"⚠️ Status check failed: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️ Status check error: {e}")

def main():
    """Main test function"""
    print("🧪 AUTHENTICATED BULK UPLOAD TEST")
    print("=" * 50)
    
    success = test_bulk_upload_with_auth()
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 TEST PASSED! The Excel file upload works correctly")
        print("✅ You can now upload all 4 files using the endpoint")
        print("\n📋 Upload sequence:")
        print("1. Upload part_1.xlsx ✅")
        print("2. Wait 30 seconds")
        print("3. Upload part_2.xlsx")
        print("4. Wait 30 seconds") 
        print("5. Upload part_3.xlsx")
        print("6. Wait 30 seconds")
        print("7. Upload part_4.xlsx")
        print("\n💡 Each upload will return a job_id to track progress")
    else:
        print("💥 TEST FAILED! Check the error messages above")

if __name__ == "__main__":
    main()
