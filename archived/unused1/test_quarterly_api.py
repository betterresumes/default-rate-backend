#!/usr/bin/env python3
"""
Test quarterly upload with admin credentials
"""

import requests
import json
import time

def test_quarterly_upload():
    base_url = "http://localhost:8000/api"
    
    # Use default admin credentials
    print("🔐 Testing login with admin user...")
    login_response = requests.post(
        f"{base_url}/auth/login",
        json={
            "email": "admin@example.com", 
            "password": "AdminPassword123!"
        }
    )
    
    print(f"Login Status: {login_response.status_code}")
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        print("🔧 Let's try to create users first...")
        
        # Try to create users
        print("Creating users...")
        import subprocess
        result = subprocess.run([
            "python3", "config/create_users.py"
        ], cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend", 
           capture_output=True, text=True, env={"PYTHONPATH": "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend"})
        
        print(f"Create users result: {result.returncode}")
        if result.stdout:
            print(f"STDOUT: {result.stdout}")
        if result.stderr:
            print(f"STDERR: {result.stderr}")
            
        # Try login again
        print("🔐 Trying login again...")
        login_response = requests.post(
            f"{base_url}/auth/login",
            json={
                "email": "admin@example.com", 
                "password": "AdminPassword123!"
            }
        )
        print(f"Login Status: {login_response.status_code}")
        if login_response.status_code != 200:
            print(f"Login still failed: {login_response.text}")
            return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"✅ Login successful!")
    
    # Test quarterly upload
    print("\n📊 Testing quarterly bulk upload...")
    
    file_path = "quarterly_upload_files/quarterly_test_10_records.xlsx"
    
    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': (file_path, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            data = {
                'prediction_type': 'quarterly'
            }
            
            print(f"📤 Uploading: {file_path}")
            print(f"📋 Data: {data}")
            
            response = requests.post(
                f"{base_url}/predictions/bulk-predict-async",
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            
            try:
                response_json = response.json()
                print(f"📝 Response JSON: {json.dumps(response_json, indent=2)}")
            except:
                print(f"📝 Response Text: {response.text}")
                
            if response.status_code == 200:
                job_info = response.json()
                job_id = job_info.get("job_id")
                print(f"✅ Job submitted successfully! Job ID: {job_id}")
                
                # Monitor the job briefly
                print("\n📊 Monitoring job progress...")
                for i in range(6):  # Check for up to 30 seconds
                    time.sleep(5)
                    status_response = requests.get(
                        f"{base_url}/predictions/job-status/{job_id}",
                        headers=headers
                    )
                    
                    if status_response.status_code == 200:
                        status_info = status_response.json()
                        status = status_info.get("status", "UNKNOWN")
                        print(f"📈 Job Status ({i*5}s): {status}")
                        
                        if status in ["SUCCESS", "FAILURE"]:
                            print(f"🎯 Final Status: {json.dumps(status_info, indent=2)}")
                            break
                    else:
                        print(f"❌ Status check failed: {status_response.status_code}")
                        break
            else:
                print(f"❌ Upload failed with status {response.status_code}")
                
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_quarterly_upload()
