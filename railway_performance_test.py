#!/usr/bin/env python3
"""
Railway Deployment Performance Test Script
Tests bulk upload API performance on Railway deployment
"""

import requests
import time
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import asyncio
import aiohttp
from datetime import datetime
import statistics

# Configuration
BASE_URL = "https://default-rate-backend-production.up.railway.app"
BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwNjhlOTNhYy03ZDBkLTQ0MzctOGRiZC0yYWExZGVhNjRlNzEiLCJleHAiOjE3NTg4NDg0MTF9.ffokqOiVaj0N1XjslRBjk5W2zGR2W6xexU1OHYlgSfA"

# Test files configuration
TEST_FILES = [
    # Annual files
    {"file": "test_data/annual_test_10_rows.xlsx", "rows": 10, "type": "annual"},
    {"file": "test_data/annual_test_20_rows.xlsx", "rows": 20, "type": "annual"},
    {"file": "test_data/annual_test_50_rows.xlsx", "rows": 50, "type": "annual"},
    {"file": "test_data/annual_test_100_rows.xlsx", "rows": 100, "type": "annual"},
    # Quarterly files
    {"file": "test_data/quarterly_test_10_rows.xlsx", "rows": 10, "type": "quarterly"},
    {"file": "test_data/quarterly_test_20_rows.xlsx", "rows": 20, "type": "quarterly"},
    {"file": "test_data/quarterly_test_50_rows.xlsx", "rows": 50, "type": "quarterly"},
    {"file": "test_data/quarterly_test_100_rows.xlsx", "rows": 100, "type": "quarterly"},
]

class RailwayPerformanceTester:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "accept": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.results = []
        
    def test_api_connectivity(self) -> bool:
        """Test if the API is accessible"""
        try:
            print("🔍 Testing API connectivity...")
            response = self.session.get(f"{BASE_URL}/docs")
            if response.status_code == 200:
                print("✅ API is accessible")
                return True
            else:
                print(f"❌ API returned status code: {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ API connection failed: {str(e)}")
            return False
    
    def upload_file_and_track(self, file_path: str, file_type: str, rows: int) -> Dict:
        """Upload file and track the complete process"""
        print(f"\n🚀 Testing {file_path} ({rows} rows, {file_type} type)")
        
        start_time = time.time()
        
        try:
            # Step 1: Upload file
            upload_start = time.time()
            
            with open(file_path, 'rb') as f:
                files = {'file': (Path(file_path).name, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                
                endpoint = f"{BASE_URL}/api/v1/predictions/{file_type}/bulk-upload-async"
                response = self.session.post(endpoint, files=files)
            
            upload_time = time.time() - upload_start
            
            if response.status_code != 200:
                print(f"❌ Upload failed with status {response.status_code}")
                print(f"Response: {response.text}")
                return {"error": "Upload failed", "status_code": response.status_code}
            
            result_data = response.json()
            job_id = result_data.get('job_id')
            
            print(f"✅ File uploaded successfully in {upload_time:.2f}s")
            print(f"📝 Job ID: {job_id}")
            
            if not job_id:
                return {"error": "No job_id returned"}
            
            # Step 2: Track job progress
            processing_start = time.time()
            job_result = self.track_job_progress(job_id)
            processing_time = time.time() - processing_start
            
            total_time = time.time() - start_time
            
            # Calculate performance metrics
            result = {
                "file": file_path,
                "rows": rows,
                "type": file_type,
                "job_id": job_id,
                "upload_time": upload_time,
                "processing_time": processing_time,
                "total_time": total_time,
                "time_per_row": total_time / rows,
                "rows_per_second": rows / total_time,
                "time_per_100_rows": (total_time / rows) * 100,
                "job_status": job_result.get("status", "unknown"),
                "successful_rows": job_result.get("successful_rows", 0),
                "failed_rows": job_result.get("failed_rows", 0),
                "error_message": job_result.get("error_message"),
            }
            
            print(f"📊 Results:")
            print(f"   Total Time: {total_time:.2f}s")
            print(f"   Time per Row: {result['time_per_row']:.3f}s")
            print(f"   Time per 100 Rows: {result['time_per_100_rows']:.2f}s")
            print(f"   Rows per Second: {result['rows_per_second']:.2f}")
            print(f"   Success Rate: {result['successful_rows']}/{rows} rows")
            
            return result
            
        except Exception as e:
            print(f"❌ Error during testing: {str(e)}")
            return {"error": str(e), "file": file_path, "rows": rows}
    
    def track_job_progress(self, job_id: str, timeout: int = 300) -> Dict:
        """Track job progress until completion"""
        print(f"⏳ Tracking job progress for {job_id}")
        
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < timeout:
            try:
                response = self.session.get(f"{BASE_URL}/api/v1/predictions/jobs/{job_id}/status")
                
                if response.status_code != 200:
                    print(f"❌ Status check failed: {response.status_code}")
                    return {"status": "error", "message": f"Status check failed: {response.status_code}"}
                
                job_data = response.json()
                current_status = job_data.get('job', {}).get('status')
                processed_rows = job_data.get('job', {}).get('processed_rows', 0)
                total_rows = job_data.get('job', {}).get('total_rows', 0)
                
                if current_status != last_status:
                    print(f"📈 Status: {current_status} | Progress: {processed_rows}/{total_rows}")
                    last_status = current_status
                
                if current_status in ['completed', 'failed']:
                    print(f"✅ Job {current_status}!")
                    return job_data.get('job', job_data)
                
                time.sleep(2)  # Check every 2 seconds
                
            except Exception as e:
                print(f"❌ Error checking job status: {str(e)}")
                return {"status": "error", "message": str(e)}
        
        print(f"⏰ Job tracking timed out after {timeout}s")
        return {"status": "timeout"}
    
    def run_all_tests(self):
        """Run all performance tests"""
        print("🎯 Starting Railway Performance Tests")
        print("=" * 60)
        
        if not self.test_api_connectivity():
            print("❌ Cannot proceed without API connectivity")
            return
        
        # Run tests for each file
        for test_config in TEST_FILES:
            result = self.upload_file_and_track(
                test_config["file"],
                test_config["type"],
                test_config["rows"]
            )
            self.results.append(result)
            
            # Small delay between tests
            time.sleep(3)
        
        # Generate comprehensive report
        self.generate_performance_report()
    
    def generate_performance_report(self):
        """Generate detailed performance analysis report"""
        print("\n" + "=" * 80)
        print("📊 COMPREHENSIVE PERFORMANCE REPORT")
        print("=" * 80)
        
        # Filter successful results
        successful_results = [r for r in self.results if "error" not in r and r.get("job_status") == "completed"]
        
        if not successful_results:
            print("❌ No successful tests to analyze")
            return
        
        # Overall statistics
        total_tests = len(self.results)
        successful_tests = len(successful_results)
        success_rate = (successful_tests / total_tests) * 100
        
        print(f"📈 OVERALL STATISTICS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Successful: {successful_tests}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        # Performance by row count
        print(f"\n📊 PERFORMANCE BY ROW COUNT:")
        print("-" * 50)
        
        row_counts = sorted(set(r["rows"] for r in successful_results))
        
        for row_count in row_counts:
            row_results = [r for r in successful_results if r["rows"] == row_count]
            
            if row_results:
                times = [r["total_time"] for r in row_results]
                time_per_row = [r["time_per_row"] for r in row_results]
                
                print(f"\n🔢 {row_count} Rows:")
                print(f"   Tests: {len(row_results)}")
                print(f"   Avg Total Time: {statistics.mean(times):.2f}s")
                print(f"   Min/Max Time: {min(times):.2f}s / {max(times):.2f}s")
                print(f"   Avg Time per Row: {statistics.mean(time_per_row):.3f}s")
                print(f"   Est. Time for 100 Rows: {statistics.mean(time_per_row) * 100:.2f}s")
        
        # Performance by type (Annual vs Quarterly)
        print(f"\n📊 PERFORMANCE BY TYPE:")
        print("-" * 50)
        
        for data_type in ["annual", "quarterly"]:
            type_results = [r for r in successful_results if r["type"] == data_type]
            
            if type_results:
                times = [r["total_time"] for r in type_results]
                time_per_row = [r["time_per_row"] for r in type_results]
                
                print(f"\n📈 {data_type.title()} Data:")
                print(f"   Tests: {len(type_results)}")
                print(f"   Avg Total Time: {statistics.mean(times):.2f}s")
                print(f"   Avg Time per Row: {statistics.mean(time_per_row):.3f}s")
                print(f"   Avg Rows per Second: {1/statistics.mean(time_per_row):.2f}")
        
        # Scaling estimates
        print(f"\n🚀 SCALING ESTIMATES:")
        print("-" * 50)
        
        if successful_results:
            avg_time_per_row = statistics.mean([r["time_per_row"] for r in successful_results])
            
            print(f"Based on average time per row: {avg_time_per_row:.3f}s")
            print(f"")
            print(f"📊 Estimated Processing Times:")
            for n in [100, 500, 1000, 5000, 10000]:
                est_time = avg_time_per_row * n
                minutes = est_time / 60
                print(f"   {n:5d} rows: {est_time:6.1f}s ({minutes:4.1f} minutes)")
        
        # Detailed results table
        print(f"\n📋 DETAILED RESULTS:")
        print("-" * 100)
        print(f"{'File':<25} {'Rows':<5} {'Type':<10} {'Total(s)':<8} {'Per Row(s)':<10} {'100 Rows(s)':<12} {'Status':<10}")
        print("-" * 100)
        
        for result in self.results:
            if "error" not in result:
                print(f"{Path(result['file']).name:<25} {result['rows']:<5} {result['type']:<10} "
                      f"{result['total_time']:<8.2f} {result['time_per_row']:<10.3f} "
                      f"{result['time_per_100_rows']:<12.2f} {result.get('job_status', 'unknown'):<10}")
            else:
                print(f"{Path(result.get('file', 'unknown')).name:<25} {result.get('rows', 0):<5} "
                      f"{'error':<10} {'ERROR':<8} {'ERROR':<10} {'ERROR':<12} {'FAILED':<10}")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"performance_report_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "base_url": BASE_URL,
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": success_rate,
                "results": self.results
            }, f, indent=2)
        
        print(f"\n💾 Detailed report saved to: {report_file}")
        print("=" * 80)

def main():
    """Main function to run performance tests"""
    tester = RailwayPerformanceTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()
