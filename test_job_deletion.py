#!/usr/bin/env python3
"""
Test script to debug job deletion issue
"""

import requests
import json
import os
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

def test_job_deletion():
    """Test job deletion with different statuses"""
    print("🧪 Testing Job Deletion API")
    print("=" * 50)
    
    # First, let's check what jobs exist
    try:
        print("📋 Getting current jobs...")
        response = requests.get(f"{API_BASE}/predictions/jobs")
        
        if response.status_code == 200:
            jobs_data = response.json()
            if jobs_data.get("success") and jobs_data.get("data"):
                jobs = jobs_data["data"]
                print(f"Found {len(jobs)} jobs:")
                
                for job in jobs[:5]:  # Show first 5 jobs
                    print(f"  • Job ID: {job['id']}")
                    print(f"    Status: {job['status']}")
                    print(f"    Type: {job['job_type']}")
                    print(f"    Filename: {job['original_filename']}")
                    print()
                
                # Try to delete the first job if it's not processing
                if jobs:
                    test_job = jobs[0]
                    job_id = test_job['id']
                    status = test_job['status']
                    
                    print(f"🗑️  Attempting to delete job {job_id} (status: {status})...")
                    
                    # Attempt deletion
                    delete_response = requests.delete(f"{API_BASE}/predictions/jobs/{job_id}")
                    
                    print(f"Response Status: {delete_response.status_code}")
                    print(f"Response Headers: {dict(delete_response.headers)}")
                    
                    try:
                        response_data = delete_response.json()
                        print(f"Response Body: {json.dumps(response_data, indent=2)}")
                    except:
                        print(f"Response Text: {delete_response.text}")
                    
                    if delete_response.status_code == 200:
                        print("✅ Job deletion successful!")
                    else:
                        print(f"❌ Job deletion failed with status {delete_response.status_code}")
                        
                        if delete_response.status_code == 400:
                            print("This suggests a business logic error (job cannot be deleted)")
                        elif delete_response.status_code == 401:
                            print("This suggests an authentication error")
                        elif delete_response.status_code == 403:
                            print("This suggests a permission error")
                        elif delete_response.status_code == 404:
                            print("This suggests the job was not found or access denied")
                
            else:
                print("No jobs found or response format issue")
                print(f"Response: {jobs_data}")
        else:
            print(f"❌ Failed to get jobs: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Error during job deletion test: {e}")

def test_job_creation_and_deletion():
    """Test creating and then deleting a job"""
    print("\n🧪 Testing Job Creation and Deletion")
    print("=" * 50)
    
    # This would require authentication, so let's skip for now
    print("⚠️  Job creation test skipped (requires authentication)")

if __name__ == "__main__":
    test_job_deletion()
    test_job_creation_and_deletion()
