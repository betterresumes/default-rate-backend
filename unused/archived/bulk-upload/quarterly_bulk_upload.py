#!/usr/bin/env python3
"""
Quarterly Bulk Upload Script

This script uploads quarterly prediction files to the system and monitors the processing.
Similar to the annual bulk upload but specifically for quarterly data.
"""

import requests
import time
import json
import os
from pathlib import Path

# Configuration
API_BASE_URL = "http://localhost:8000"
LOGIN_EMAIL = "patil@gmail.com"
LOGIN_PASSWORD = "Test123*"

# Quarterly files to upload
QUARTERLY_FILES = [
    "quarterly_upload_files/quarterly_predictions_part_1.xlsx",
    "quarterly_upload_files/quarterly_predictions_part_2.xlsx", 
    "quarterly_upload_files/quarterly_predictions_part_3.xlsx",
    "quarterly_upload_files/quarterly_predictions_part_4.xlsx"
]

class QuarterlyBulkUploader:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        
    def authenticate(self):
        """Authenticate and get access token"""
        print("🔐 Authenticating...")
        
        login_data = {
            "email": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD
        }
        
        response = self.session.post(
            f"{API_BASE_URL}/api/auth/login",
            json=login_data
        )
        
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("access_token")
            print("✅ Authentication successful!")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(response.text)
            return False
    
    def check_health(self):
        """Check if the API is healthy"""
        print("🏥 Checking system health...")
        
        try:
            response = self.session.get(f"{API_BASE_URL}/health")
            if response.status_code == 200:
                health_data = response.json()
                print("✅ System is healthy!")
                
                # Check services
                services = health_data.get("services", {})
                for service, status in services.items():
                    if isinstance(status, dict):
                        print(f"   {service}: {status.get('status', 'unknown')}")
                    else:
                        print(f"   {service}: {status}")
                
                return True
            else:
                print(f"❌ Health check failed: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Health check error: {e}")
            return False
    
    def upload_quarterly_file(self, file_path):
        """Upload a single quarterly file"""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return None
        
        print(f"📤 Uploading {file_path}...")
        
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        files = {
            "file": open(file_path, "rb")
        }
        
        data = {
            "prediction_type": "quarterly"  # This is the key difference from annual
        }
        
        try:
            response = self.session.post(
                f"{API_BASE_URL}/api/predictions/bulk-predict-async",
                headers=headers,
                files=files,
                data=data
            )
            
            files["file"].close()
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get("job_id")
                print(f"✅ Upload successful! Job ID: {job_id}")
                print(f"   Estimated time: {result.get('estimated_processing_time', 'Unknown')}")
                return job_id
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ Upload error: {e}")
            return None
    
    def monitor_job(self, job_id, file_name):
        """Monitor a job until completion"""
        print(f"⏳ Monitoring job {job_id} for {file_name}...")
        
        headers = {
            "Authorization": f"Bearer {self.token}"
        }
        
        start_time = time.time()
        max_wait_time = 1800  # 30 minutes max
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.session.get(
                    f"{API_BASE_URL}/api/predictions/job-status/{job_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    status = data.get("status")
                    
                    if status == "SUCCESS":
                        result = data.get("result", {})
                        successful = result.get("successful_predictions", 0)
                        failed = result.get("failed_predictions", 0)
                        total = result.get("total_processed", 0)
                        
                        print(f"🎉 {file_name} completed successfully!")
                        print(f"   📊 Total: {total}, Success: {successful}, Failed: {failed}")
                        
                        # Show sample results
                        results = result.get("results", [])
                        if results:
                            print("   📋 Sample results:")
                            for i, res in enumerate(results[:3]):
                                pred = res.get("prediction", {})
                                print(f"      {i+1}. {res.get('stock_symbol')} ({pred.get('reporting_year')}-{pred.get('reporting_quarter')}) - "
                                      f"Risk: {pred.get('risk_level')}, "
                                      f"Probability: {pred.get('primary_probability', 0):.4f}")
                        
                        return True
                        
                    elif status == "FAILURE":
                        error = data.get("error", "Unknown error")
                        print(f"❌ {file_name} failed: {error}")
                        return False
                        
                    elif status == "PROGRESS":
                        progress = data.get("progress", {})
                        current = progress.get("current", 0)
                        total = progress.get("total", 0)
                        print(f"   📈 Progress: {current}/{total} ({(current/total*100):.1f}%)")
                        
                    elif status == "PENDING":
                        print(f"   ⏸️  Job is pending...")
                    
                    time.sleep(10)  # Wait 10 seconds before next check
                    
                else:
                    print(f"❌ Status check failed: {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"❌ Monitoring error: {e}")
                return False
        
        print(f"⏰ Timeout waiting for {file_name} to complete")
        return False
    
    def upload_all_quarterly_files(self):
        """Upload all quarterly files"""
        print("🚀 Starting quarterly bulk upload process...")
        print(f"📁 Files to upload: {len(QUARTERLY_FILES)}")
        
        results = []
        
        for i, file_path in enumerate(QUARTERLY_FILES, 1):
            print(f"\n📦 Processing file {i}/{len(QUARTERLY_FILES)}: {file_path}")
            
            # Upload the file
            job_id = self.upload_quarterly_file(file_path)
            if not job_id:
                results.append({"file": file_path, "status": "upload_failed"})
                continue
            
            # Monitor the job
            success = self.monitor_job(job_id, Path(file_path).name)
            results.append({
                "file": file_path,
                "job_id": job_id,
                "status": "success" if success else "failed"
            })
            
            if i < len(QUARTERLY_FILES):
                print(f"⏸️  Waiting 5 seconds before next upload...")
                time.sleep(5)
        
        return results
    
    def print_summary(self, results):
        """Print upload summary"""
        print("\n" + "="*60)
        print("📊 QUARTERLY BULK UPLOAD SUMMARY")
        print("="*60)
        
        successful = len([r for r in results if r["status"] == "success"])
        failed = len([r for r in results if r["status"] != "success"])
        
        print(f"✅ Successful uploads: {successful}")
        print(f"❌ Failed uploads: {failed}")
        print(f"📁 Total files: {len(results)}")
        
        print("\n📋 Detailed results:")
        for result in results:
            status_emoji = "✅" if result["status"] == "success" else "❌"
            file_name = Path(result["file"]).name
            print(f"   {status_emoji} {file_name}: {result['status']}")
        
        if successful > 0:
            print(f"\n🎉 Quarterly bulk upload completed! {successful} files processed successfully.")
        else:
            print(f"\n😞 No files were processed successfully. Please check the errors above.")

def main():
    """Main execution function"""
    print("🔄 Quarterly Bulk Upload System")
    print("="*40)
    
    uploader = QuarterlyBulkUploader()
    
    # Check system health
    if not uploader.check_health():
        print("❌ System health check failed. Please start the system first.")
        return
    
    # Authenticate
    if not uploader.authenticate():
        print("❌ Authentication failed. Please check credentials.")
        return
    
    # Upload all files
    results = uploader.upload_all_quarterly_files()
    
    # Print summary
    uploader.print_summary(results)

if __name__ == "__main__":
    main()
