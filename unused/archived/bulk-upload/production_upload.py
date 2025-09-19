#!/usr/bin/env python3
"""
Production Upload Script: Upload all 4 Excel files sequentially with delays
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

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
            return None
            
    except Exception as e:
        print(f"❌ Login error: {e}")
        return None

def upload_file(file_path, token, file_number, total_files):
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
        print(f"\n🚀 [{file_number}/{total_files}] Uploading {file_path.name}...")
        print(f"⏰ Time: {datetime.now().strftime('%H:%M:%S')}")
        
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
            total_companies = result.get('total_companies', 0)
            
            print(f"✅ Upload successful!")
            print(f"🆔 Job ID: {job_id}")
            print(f"👥 Companies: {total_companies}")
            
            return {
                'job_id': job_id,
                'file_name': file_path.name,
                'companies': total_companies,
                'upload_time': datetime.now().strftime('%H:%M:%S')
            }
            
        else:
            print(f"❌ Upload failed with status {response.status_code}")
            try:
                error_details = response.json()
                print(f"📋 Error: {error_details}")
            except:
                print(f"📋 Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        return None
    finally:
        files['file'][1].close()

def check_all_job_status(jobs, token):
    """Check status of all jobs"""
    base_url = "http://localhost:8000"
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    print(f"\n📊 CHECKING ALL JOB STATUSES")
    print("=" * 60)
    
    for i, job in enumerate(jobs, 1):
        if not job:
            continue
            
        job_id = job['job_id']
        file_name = job['file_name']
        
        try:
            response = requests.get(
                f"{base_url}/api/predictions/bulk-job-status/{job_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                status_data = response.json()
                status = status_data.get('status', 'UNKNOWN')
                progress = status_data.get('progress', {})
                
                print(f"[{i}] {file_name}")
                print(f"    🆔 Job ID: {job_id}")
                print(f"    📊 Status: {status}")
                print(f"    ⏰ Upload Time: {job['upload_time']}")
                print(f"    👥 Companies: {job['companies']}")
                if progress:
                    processed = progress.get('processed', 0)
                    total = progress.get('total', 0)
                    print(f"    📈 Progress: {processed}/{total}")
                print()
                
            else:
                print(f"[{i}] {file_name} - Status check failed: {response.status_code}")
                
        except Exception as e:
            print(f"[{i}] {file_name} - Status check error: {e}")

def main():
    """Main production upload function"""
    print("🚀 PRODUCTION ANNUAL PREDICTIONS UPLOAD")
    print("=" * 60)
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Get authentication token
    token = login_and_get_token()
    if not token:
        print("💥 Could not get authentication token")
        return
    
    # Define files to upload
    files_to_upload = [
        'bulk_upload_files/annual_predictions_part_1.xlsx',
        'bulk_upload_files/annual_predictions_part_2.xlsx',
        'bulk_upload_files/annual_predictions_part_3.xlsx',
        'bulk_upload_files/annual_predictions_part_4.xlsx'
    ]
    
    jobs = []
    total_files = len(files_to_upload)
    
    # Upload each file with delays
    for i, file_path_str in enumerate(files_to_upload, 1):
        file_path = Path(file_path_str)
        
        # Upload file
        job_info = upload_file(file_path, token, i, total_files)
        jobs.append(job_info)
        
        # Wait 30 seconds between uploads (except for the last file)
        if i < total_files:
            print(f"⏰ Waiting 30 seconds before next upload...")
            time.sleep(30)
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 UPLOAD SUMMARY")
    print("=" * 60)
    
    successful_uploads = [job for job in jobs if job is not None]
    total_companies = sum(job['companies'] for job in successful_uploads)
    
    print(f"✅ Successful uploads: {len(successful_uploads)}/{total_files}")
    print(f"👥 Total companies: {total_companies}")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if successful_uploads:
        print(f"\n🆔 JOB IDS:")
        for job in successful_uploads:
            print(f"  {job['file_name']}: {job['job_id']}")
        
        # Check initial status of all jobs
        print(f"\n⏰ Waiting 30 seconds before status check...")
        time.sleep(30)
        check_all_job_status(jobs, token)
        
        print(f"\n💡 To check job status later, use:")
        for job in successful_uploads:
            print(f"  curl -H 'Authorization: Bearer {token[:20]}...' http://localhost:8000/api/predictions/bulk-job-status/{job['job_id']}")
    
    print(f"\n🎉 Production upload completed!")
    print(f"💡 Monitor the logs and database for processing progress")

if __name__ == "__main__":
    main()
