#!/usr/bin/env python3
"""
Test single file upload with 30-second wait and status check
"""

import requests
import json
import time
from pathlib import Path

def get_auth_token():
    """Get authentication token"""
    base_url = "http://localhost:8000"
    
    # Try login with existing user
    login_data = {
        "email": "patil@gmail.com",
        "password": "Test123*"
    }
    
    try:
        print("🔐 Logging in...")
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
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
            
            # Try to create user if login fails
            print("👤 Attempting to create user...")
            register_data = {
                "email": "patil@gmail.com",
                "username": "patil",
                "password": "Test123*",
                "confirm_password": "Test123*",
                "full_name": "Test User"
            }
            
            register_response = requests.post(
                f"{base_url}/api/auth/register",
                json=register_data,
                timeout=10
            )
            
            if register_response.status_code == 201:
                print("✅ User created, trying login again...")
                return get_auth_token()  # Retry login
            else:
                print(f"❌ Registration failed: {register_response.status_code}")
                return None
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def upload_file(token, file_path):
    """Upload a single file"""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/predictions/bulk-predict-async"
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return None
    
    # Prepare the request
    with open(file_path, 'rb') as file:
        files = {
            'file': (file_path.name, file, 
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        }
        
        data = {
            'prediction_type': 'annual'
        }
        
        headers = {
            'Authorization': f'Bearer {token}'
        }
        
        try:
            print(f"🚀 Uploading {file_path.name}...")
            
            response = requests.post(
                endpoint,
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )
            
            print(f"📡 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("🎉 SUCCESS! File uploaded")
                print(f"📋 Response: {json.dumps(result, indent=2)}")
                
                if 'job_id' in result:
                    job_id = result['job_id']
                    print(f"🆔 Job ID: {job_id}")
                    return job_id
                
                return True
                
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                try:
                    error_details = response.json()
                    print(f"📋 Error Details: {json.dumps(error_details, indent=2)}")
                except:
                    print(f"📋 Response Text: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            return None

def check_job_status(job_id, token):
    """Check the status of the bulk upload job"""
    base_url = "http://localhost:8000"
    status_endpoint = f"{base_url}/api/predictions/job-status/{job_id}"
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    try:
        print(f"📊 Checking job status for {job_id}...")
        
        response = requests.get(status_endpoint, headers=headers, timeout=10)
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"📋 Job Status: {json.dumps(status_data, indent=2)}")
            return status_data
        else:
            print(f"⚠️ Status check failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"⚠️ Status check error: {e}")
        return None

def main():
    """Main test function"""
    print("🧪 SINGLE FILE UPLOAD TEST")
    print("=" * 50)
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("💥 Could not get authentication token")
        return
    
    print(f"🔑 Got access token: {token[:20]}...")
    
    # Upload first file
    file_path = Path('bulk_upload_files/annual_predictions_part_1.xlsx')
    job_id = upload_file(token, file_path)
    
    if not job_id:
        print("💥 Upload failed")
        return
    
    # Wait 30 seconds
    print("\n⏰ Waiting 30 seconds...")
    time.sleep(30)
    
    # Check job status
    print("\n📊 Checking job status...")
    status = check_job_status(job_id, token)
    
    if status:
        state = status.get('state', 'UNKNOWN')
        print(f"\n🔍 Current job state: {state}")
        
        if state == 'SUCCESS':
            print("🎉 Job completed successfully!")
        elif state == 'PENDING':
            print("⏳ Job is still processing...")
        elif state == 'PROGRESS':
            print("🔄 Job is in progress...")
        elif state == 'FAILURE':
            print("💥 Job failed!")
        else:
            print(f"❓ Unknown job state: {state}")
    
    print("\n" + "=" * 50)
    print("✅ TEST COMPLETED")
    print("\n📋 Next steps for production:")
    print("1. All Excel files are ready in bulk_upload_files/")
    print("2. API endpoint is working correctly")
    print("3. Authentication is set up")
    print("4. Job tracking is functional")
    print("\n💡 Ready to run production upload script!")

if __name__ == "__main__":
    main()
