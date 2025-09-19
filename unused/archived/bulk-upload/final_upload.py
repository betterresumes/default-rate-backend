#!/usr/bin/env python3
"""
Final Production Upload Script: Upload all 4 Excel files sequentially
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

def get_auth_token():
    """Get authentication token"""
    base_url = "http://localhost:8000"
    
    login_data = {
        "email": "patil@gmail.com",
        "password": "Test123*"
    }
    
    try:
        print("🔐 Authenticating...")
        login_response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if login_response.status_code == 200:
            token_data = login_response.json()
            access_token = token_data["access_token"]
            print("✅ Authentication successful")
            return access_token
        else:
            print(f"❌ Authentication failed: {login_response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Authentication error: {e}")
        return None

def upload_file(token, file_path, file_number, total_files):
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
            print(f"🚀 Uploading file {file_number}/{total_files}: {file_path.name}")
            print(f"   📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            response = requests.post(
                endpoint,
                files=files,
                data=data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                
                print(f"   ✅ Upload successful!")
                print(f"   🆔 Job ID: {job_id}")
                
                if 'companies' in result.get('message', ''):
                    # Extract number from message like "2475 companies submitted for processing"
                    parts = result.get('message', '').split()
                    if len(parts) > 0 and parts[0].isdigit():
                        count = parts[0]
                        print(f"   📊 Companies submitted: {count}")
                
                return job_id
                
            else:
                print(f"   ❌ Upload failed with status {response.status_code}")
                try:
                    error_details = response.json()
                    print(f"   📋 Error: {json.dumps(error_details, indent=6)}")
                except:
                    print(f"   📋 Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"   ❌ Upload error: {e}")
            return None

def check_job_status(job_id, token, file_name):
    """Check the status of the bulk upload job"""
    base_url = "http://localhost:8000"
    status_endpoint = f"{base_url}/api/predictions/job-status/{job_id}"
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    try:
        response = requests.get(status_endpoint, headers=headers, timeout=10)
        
        if response.status_code == 200:
            status_data = response.json()
            state = status_data.get('state', 'UNKNOWN')
            
            print(f"   📊 {file_name} Status: {state}")
            
            if 'result' in status_data and status_data['result']:
                result = status_data['result']
                if isinstance(result, dict):
                    successful = result.get('successful_predictions', 0)
                    failed = result.get('failed_predictions', 0)
                    print(f"   📈 Successful: {successful}, Failed: {failed}")
            
            return status_data
        else:
            print(f"   ⚠️ Status check failed: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"   ⚠️ Status check error: {e}")
        return None

def main():
    """Main production upload function"""
    print("🚀 FINAL PRODUCTION ANNUAL PREDICTIONS UPLOAD")
    print("=" * 60)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get authentication token
    token = get_auth_token()
    if not token:
        print("💥 Authentication failed - exiting")
        return
    
    # Define files to upload
    files_to_upload = [
        'bulk_upload_files/annual_predictions_part_1.xlsx',
        'bulk_upload_files/annual_predictions_part_2.xlsx',
        'bulk_upload_files/annual_predictions_part_3.xlsx',
        'bulk_upload_files/annual_predictions_part_4.xlsx'
    ]
    
    job_ids = []
    
    # Upload each file with 30-second delays
    for i, file_path_str in enumerate(files_to_upload, 1):
        file_path = Path(file_path_str)
        
        print(f"\n📁 Processing file {i}/{len(files_to_upload)}")
        print("-" * 40)
        
        # Upload file
        job_id = upload_file(token, file_path, i, len(files_to_upload))
        
        if job_id:
            job_ids.append((job_id, file_path.name))
            
            # Wait 30 seconds before next upload (except for last file)
            if i < len(files_to_upload):
                print(f"   ⏰ Waiting 30 seconds before next upload...")
                time.sleep(30)
        else:
            print(f"   💥 Failed to upload {file_path.name}")
            # Continue with other files
    
    print(f"\n🎯 UPLOAD PHASE COMPLETED")
    print("=" * 60)
    print(f"✅ Successfully uploaded: {len(job_ids)}/{len(files_to_upload)} files")
    print()
    
    if job_ids:
        print("📊 JOB STATUS SUMMARY")
        print("-" * 40)
        
        for job_id, file_name in job_ids:
            check_job_status(job_id, token, file_name)
        
        print(f"\n💡 MONITORING INSTRUCTIONS")
        print("-" * 40)
        print("All uploads have been submitted. Here are your job IDs:")
        print()
        
        for i, (job_id, file_name) in enumerate(job_ids, 1):
            print(f"{i}. {file_name}")
            print(f"   Job ID: {job_id}")
            print(f"   Status URL: http://localhost:8000/api/predictions/job-status/{job_id}")
            print()
        
        print("🔍 To check progress:")
        print("- Jobs typically take 41-82 minutes to complete")
        print("- Each file contains ~2,500 companies")
        print("- Total expected: ~10,000 annual predictions")
        print()
        print("📈 Expected completion:")
        completion_time = datetime.now()
        completion_time = completion_time.replace(
            hour=(completion_time.hour + 2) % 24,
            minute=(completion_time.minute + 30) % 60
        )
        print(f"   Estimated: {completion_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
    else:
        print("💥 No files were uploaded successfully")
    
    print(f"\n🏁 Process completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
