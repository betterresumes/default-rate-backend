#!/usr/bin/env python3
"""
Quick test for quarterly bulk upload endpoint
"""

import requests
import json

def test_quarterly_endpoint():
    """Test the quarterly bulk upload endpoint"""
    base_url = "http://localhost:8000/api"
    
    # Login with correct credentials
    print("🔐 Testing login...")
    login_response = requests.post(
        f"{base_url}/auth/login",
        json={
            "email": "patil@gmail.com",
            "password": "Test123*"
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code} - {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("✅ Login successful!")
    
    # Test quarterly endpoint
    print("\n📊 Testing quarterly bulk upload...")
    
    file_path = "files/quarterly_upload_files/quarterly_test_10_records.xlsx"
    
    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': (file_path, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            
            print(f"📤 Uploading: {file_path}")
            
            response = requests.post(
                f"{base_url}/predictions/quarterly-bulk-predict",
                files=files,
                headers=headers,
                timeout=60
            )
            
            print(f"📥 Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_json = response.json()
                print(f"✅ Success! Processed {response_json.get('processed_records', 0)} records")
                print(f"📊 Summary: {response_json.get('message', 'No message')}")
            else:
                print(f"❌ Failed: {response.text}")
                
    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
        # Try alternative path
        alt_path = "quarterly_upload_files/quarterly_test_10_records.xlsx"
        try:
            with open(alt_path, 'rb') as f:
                files = {
                    'file': (alt_path, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                }
                
                print(f"📤 Trying alternative path: {alt_path}")
                
                response = requests.post(
                    f"{base_url}/predictions/quarterly-bulk-predict",
                    files=files,
                    headers=headers,
                    timeout=60
                )
                
                print(f"📥 Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    response_json = response.json()
                    print(f"✅ Success! Processed {response_json.get('processed_records', 0)} records")
                else:
                    print(f"❌ Failed: {response.text}")
                    
        except FileNotFoundError:
            print(f"❌ File not found in either location")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_quarterly_endpoint()
