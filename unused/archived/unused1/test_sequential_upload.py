#!/usr/bin/env python3
"""
Sequential test: Upload 1 file, wait 30 seconds, check status, prepare for production
"""

import requests
import json
import time
from pathlib import Path

def login_and_get_token():
    """Login to get authentication token"""
    base_url = "http://localhost:8000"
    
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
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def upload_file(file_path, token):
    """Upload a single file and return job_id"""
    base_url = "http://localhost:8000"
    endpoint = f"{base_url}/api/predictions/bulk-predict-async"
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return None
    
    files = {
        'file': (file_path.name, open(file_path, 'rb'), 
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
            print("🎉 Upload successful!")
            print(f"📋 Response: {json.dumps(result, indent=2)}")
            
            if 'job_id' in result:
                job_id = result['job_id']
                print(f"🆔 Job ID: {job_id}")
                return job_id
            
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
    finally:
        files['file'][1].close()

def check_job_status(job_id, token):
    """Check the status of a job"""
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
            return status_data
        else:
            print(f"⚠️ Status check failed: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"⚠️ Status check error: {e}")
        return None

def cleanup_test_files():
    """Remove test files to prepare for production"""
    print("\n🧹 CLEANUP: Removing test files...")
    
    test_files = [
        "test_bulk_upload_auth.py",
        "test_sequential_upload.py"
    ]
    
    for filename in test_files:
        file_path = Path(filename)
        if file_path.exists():
            try:
                file_path.unlink()
                print(f"🗑️ Removed {filename}")
            except Exception as e:
                print(f"⚠️ Could not remove {filename}: {e}")

def main():
    """Main test function"""
    print("🧪 SEQUENTIAL UPLOAD TEST")
    print("=" * 50)
    
    # Get authentication token
    token = login_and_get_token()
    if not token:
        print("💥 Could not get authentication token")
        return
    
    # Upload first file
    file_path = Path('bulk_upload_files/annual_predictions_part_1.xlsx')
    job_id = upload_file(file_path, token)
    
    if not job_id:
        print("💥 Upload failed")
        return
    
    print(f"\n⏰ Waiting 30 seconds before checking status...")
    time.sleep(30)
    
    # Check job status
    status = check_job_status(job_id, token)
    
    print("\n" + "=" * 50)
    print("📋 TEST RESULTS:")
    print(f"✅ File uploaded successfully")
    print(f"🆔 Job ID: {job_id}")
    
    if status:
        job_status = status.get('status', 'UNKNOWN')
        progress = status.get('progress', {})
        print(f"📊 Status: {job_status}")
        if progress:
            print(f"📈 Progress: {progress}")
    
    print("\n🚀 READY FOR PRODUCTION!")
    print("To upload all files, run:")
    print("python production_upload.py")
    
    # Clean up test files
    cleanup_test_files()

if __name__ == "__main__":
    main()
