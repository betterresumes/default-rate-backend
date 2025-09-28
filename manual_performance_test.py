#!/usr/bin/env python3
"""
Manual Performance Testing Script for Railway Deployment
Run this to test your bulk upload APIs performance
"""

import requests
import json
import time
from pathlib import Path
from datetime import datetime

def test_upload(base_url: str, bearer_token: str, file_path: str, endpoint: str):
    """Test a single file upload"""
    print(f"\n🚀 Testing: {Path(file_path).name}")
    
    headers = {'Authorization': f'Bearer {bearer_token}'}
    
    # Upload file
    start_time = time.time()
    with open(file_path, 'rb') as f:
        files = {'file': (Path(file_path).name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
        
        upload_response = requests.post(
            f"{base_url}{endpoint}",
            headers=headers,
            files=files,
            timeout=60
        )
    
    upload_time = time.time() - start_time
    
    if upload_response.status_code != 200:
        print(f"❌ Upload failed: {upload_response.status_code}")
        print(f"Response: {upload_response.text}")
        return None
    
    upload_data = upload_response.json()
    job_id = upload_data.get('job_id')
    
    print(f"✅ Upload successful in {upload_time:.2f}s")
    print(f"📋 Job ID: {job_id}")
    print(f"📊 Total rows: {upload_data.get('total_rows', 'N/A')}")
    print(f"⏱️  Estimated time: {upload_data.get('estimated_time_minutes', 'N/A')} minutes")
    
    if not job_id:
        print("❌ No job_id in response")
        return None
    
    # Monitor progress
    print("⏳ Monitoring progress...")
    start_monitoring = time.time()
    checks = 0
    
    while True:
        checks += 1
        
        status_response = requests.get(
            f"{base_url}/api/v1/predictions/bulk-upload/job/{job_id}/status",
            headers=headers,
            timeout=30
        )
        
        if status_response.status_code != 200:
            print(f"❌ Status check failed: {status_response.status_code}")
            break
        
        status_data = status_response.json()
        status = status_data.get('status', 'unknown')
        processed = status_data.get('processed_rows', 0)
        successful = status_data.get('successful_rows', 0)
        failed = status_data.get('failed_rows', 0)
        
        elapsed = time.time() - start_monitoring
        
        print(f"📊 Check #{checks}: {status} | Processed: {processed} | Success: {successful} | Failed: {failed} | Elapsed: {elapsed:.1f}s")
        
        if status in ['completed', 'failed']:
            break
        
        time.sleep(3)  # Check every 3 seconds
        
        if elapsed > 300:  # 5 minute timeout
            print("❌ Timeout waiting for completion")
            break
    
    total_time = time.time() - start_monitoring
    
    # Final results
    if status == 'completed':
        processing_time = None
        if status_data.get('started_at') and status_data.get('completed_at'):
            try:
                start_dt = datetime.fromisoformat(status_data['started_at'].replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(status_data['completed_at'].replace('Z', '+00:00'))
                processing_time = (end_dt - start_dt).total_seconds()
            except:
                pass
        
        rows_per_sec = successful / processing_time if processing_time else successful / total_time if total_time > 0 else 0
        time_per_row = processing_time / successful if processing_time and successful > 0 else total_time / successful if total_time > 0 and successful > 0 else 0
        
        print(f"\n🎉 COMPLETED SUCCESSFULLY!")
        print(f"   Total monitoring time: {total_time:.2f} seconds")
        print(f"   Actual processing time: {processing_time:.2f} seconds" if processing_time else "   Processing time: N/A")
        print(f"   Successful rows: {successful}")
        print(f"   Failed rows: {failed}")
        print(f"   Rows per second: {rows_per_sec:.2f}")
        print(f"   Time per row: {time_per_row:.4f} seconds")
        print(f"   Time per 100 rows: {time_per_row * 100:.2f} seconds")
        
        return {
            'success': True,
            'rows': successful,
            'total_time': total_time,
            'processing_time': processing_time,
            'rows_per_second': rows_per_sec,
            'time_per_row': time_per_row
        }
    else:
        print(f"\n❌ FAILED: {status}")
        if status_data.get('error_message'):
            print(f"   Error: {status_data['error_message']}")
        return None

def main():
    # Configuration - UPDATE WITH YOUR ACTUAL RAILWAY URL
    BASE_URL = input("Enter your Railway URL (e.g., https://your-app.railway.app): ").strip()
    if not BASE_URL:
        BASE_URL = "https://default-rate-backend-production.up.railway.app"
    
    BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4MjAxMTZhYS01M2VjLTRhOTEtOGNmOS0zZmI5MWJhMjQ4MDYiLCJleHAiOjE3NTg4NDk2MzB9.PewO8fT1Qrtxf1kR5982JUYrenclkTU9i1_NWVAa-ZI"
    
    print("🔄 BULK UPLOAD PERFORMANCE TESTING")
    print(f"🌐 Base URL: {BASE_URL}")
    print(f"🔑 Token: {BEARER_TOKEN[:20]}...")
    
    # Test configuration
    tests = [
        ("test_data/annual_test_10_rows.xlsx", "/api/v1/predictions/annual/bulk-upload-async", "Annual"),
        ("test_data/annual_test_20_rows.xlsx", "/api/v1/predictions/annual/bulk-upload-async", "Annual"),
        ("test_data/annual_test_50_rows.xlsx", "/api/v1/predictions/annual/bulk-upload-async", "Annual"),
        ("test_data/annual_test_100_rows.xlsx", "/api/v1/predictions/annual/bulk-upload-async", "Annual"),
        ("test_data/quarterly_test_10_rows.xlsx", "/api/v1/predictions/quarterly/bulk-upload-async", "Quarterly"),
        ("test_data/quarterly_test_20_rows.xlsx", "/api/v1/predictions/quarterly/bulk-upload-async", "Quarterly"),
        ("test_data/quarterly_test_50_rows.xlsx", "/api/v1/predictions/quarterly/bulk-upload-async", "Quarterly"),
        ("test_data/quarterly_test_100_rows.xlsx", "/api/v1/predictions/quarterly/bulk-upload-async", "Quarterly"),
    ]
    
    results = []
    
    for file_path, endpoint, test_type in tests:
        if not Path(file_path).exists():
            print(f"❌ File not found: {file_path}")
            continue
        
        print(f"\n{'='*60}")
        print(f"🧪 Testing {test_type} Predictions")
        
        result = test_upload(BASE_URL, BEARER_TOKEN, file_path, endpoint)
        if result:
            result['file'] = file_path
            result['test_type'] = test_type
            results.append(result)
        
        print(f"{'='*60}")
        
        # Pause between tests
        time.sleep(5)
    
    # Summary
    print(f"\n\n🏁 FINAL SUMMARY")
    print(f"={'='*50}")
    
    annual_results = [r for r in results if r['test_type'] == 'Annual']
    quarterly_results = [r for r in results if r['test_type'] == 'Quarterly']
    
    def print_analysis(test_results, test_type):
        if not test_results:
            print(f"No successful {test_type} tests")
            return
        
        avg_rows_per_sec = sum(r['rows_per_second'] for r in test_results) / len(test_results)
        avg_time_per_row = sum(r['time_per_row'] for r in test_results) / len(test_results)
        
        print(f"\n📊 {test_type} Predictions Performance:")
        print(f"   Tests completed: {len(test_results)}")
        print(f"   Average rows/second: {avg_rows_per_sec:.2f}")
        print(f"   Average time per row: {avg_time_per_row:.4f} seconds")
        print(f"   Average time per 100 rows: {avg_time_per_row * 100:.2f} seconds")
        
        print(f"\n📈 Estimated times for larger files ({test_type}):")
        for n in [500, 1000, 2000, 5000, 10000]:
            estimated = avg_time_per_row * n
            print(f"     {n:5d} rows: ~{estimated/60:.1f} minutes ({estimated:.1f} seconds)")
    
    print_analysis(annual_results, "Annual")
    print_analysis(quarterly_results, "Quarterly")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"test_results_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': timestamp,
            'base_url': BASE_URL,
            'results': results,
            'summary': {
                'total_tests': len(results),
                'annual_avg_time_per_row': sum(r['time_per_row'] for r in annual_results) / len(annual_results) if annual_results else 0,
                'quarterly_avg_time_per_row': sum(r['time_per_row'] for r in quarterly_results) / len(quarterly_results) if quarterly_results else 0
            }
        }, f, indent=2, default=str)
    
    print(f"\n💾 Results saved to: {results_file}")

if __name__ == "__main__":
    main()
