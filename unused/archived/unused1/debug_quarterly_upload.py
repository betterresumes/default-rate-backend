#!/usr/bin/env python3
"""
Debug quarterly bulk upload API
"""

import requests
import json
import time

def debug_quarterly_upload():
    base_url = "http://localhost:8000/api"
    
    # First try to register a test user
    print("👤 Registering test user...")
    register_response = requests.post(
        f"{base_url}/auth/register",
        json={
            "email": "testuser@example.com",
            "username": "testuser",
            "password": "TestPassword123",
            "confirm_password": "TestPassword123",
            "full_name": "Test User"
        }
    )
    print(f"Registration Status: {register_response.status_code}")
    if register_response.status_code in [200, 201]:
        print("✅ User registered successfully")
    elif register_response.status_code == 400:
        print("ℹ️  User might already exist")
    
    # Test login with test user
    print("\n🔐 Testing login...")
    login_response = requests.post(
        f"{base_url}/auth/login",
        json={
            "email": "testuser@example.com",
            "password": "TestPassword123"
        }
    )
    
    print(f"Login Status: {login_response.status_code}")
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"✅ Login successful, token received")
    
    # Test quarterly upload with detailed debugging
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
            print(f"🔑 Headers: Authorization Bearer token included")
            
            response = requests.post(
                f"{base_url}/predictions/bulk-predict-async",
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )
            
            print(f"\n📥 Response Status: {response.status_code}")
            print(f"📄 Response Headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                print(f"📝 Response JSON: {json.dumps(response_json, indent=2)}")
            except:
                print(f"📝 Response Text: {response.text}")
                
            if response.status_code == 200:
                job_info = response.json()
                job_id = job_info.get("job_id")
                print(f"✅ Job submitted successfully! Job ID: {job_id}")
                
                # Monitor the job
                print("\n📊 Monitoring job progress...")
                for i in range(10):  # Check for up to 50 seconds
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
    debug_quarterly_upload()
