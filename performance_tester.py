#!/usr/bin/env python3
"""
Performance Testing Script for Bulk Upload APIs
Tests both annual and quarterly bulk upload endpoints with different file sizes
"""

import asyncio
import aiohttp
import json
import time
import statistics
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import pandas as pd

class BulkUploadPerformanceTester:
    def __init__(self, base_url: str, bearer_token: str):
        self.base_url = base_url.rstrip('/')
        self.bearer_token = bearer_token
        self.headers = {
            'Authorization': f'Bearer {bearer_token}',
            'Accept': 'application/json'
        }
        self.session = None
        self.test_results = []
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def upload_file(self, file_path: str, endpoint: str) -> Dict:
        """Upload a file to the specified endpoint and return timing info"""
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"Test file not found: {file_path}")
        
        start_time = time.time()
        
        with open(file_path, 'rb') as f:
            data = aiohttp.FormData()
            data.add_field('file', f, filename=file_path_obj.name, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            
            async with self.session.post(
                f"{self.base_url}{endpoint}",
                headers=self.headers,
                data=data
            ) as response:
                upload_time = time.time() - start_time
                response_data = await response.json()
                
                return {
                    'upload_time': upload_time,
                    'status_code': response.status,
                    'response': response_data,
                    'file_size': file_path_obj.stat().st_size,
                    'file_name': file_path_obj.name
                }
    
    async def monitor_job_progress(self, job_id: str, timeout: int = 300) -> Dict:
        """Monitor job progress until completion or timeout"""
        start_time = time.time()
        status_checks = 0
        
        while time.time() - start_time < timeout:
            status_checks += 1
            
            async with self.session.get(
                f"{self.base_url}/api/v1/predictions/bulk-upload/job/{job_id}/status",
                headers=self.headers
            ) as response:
                if response.status != 200:
                    return {
                        'error': f'Status check failed: {response.status}',
                        'total_time': time.time() - start_time,
                        'status_checks': status_checks
                    }
                
                status_data = await response.json()
                status = status_data.get('status', 'unknown')
                
                if status in ['completed', 'failed']:
                    total_time = time.time() - start_time
                    return {
                        'status': status,
                        'total_time': total_time,
                        'status_checks': status_checks,
                        'job_data': status_data,
                        'processing_time': self._calculate_processing_time(status_data),
                        'rows_per_second': self._calculate_rows_per_second(status_data, total_time)
                    }
                
                # Wait before next check
                await asyncio.sleep(2)
        
        return {
            'error': 'Timeout waiting for job completion',
            'total_time': timeout,
            'status_checks': status_checks
        }
    
    def _calculate_processing_time(self, job_data: Dict) -> Optional[float]:
        """Calculate actual processing time from job timestamps"""
        try:
            started_at = job_data.get('started_at')
            completed_at = job_data.get('completed_at')
            
            if started_at and completed_at:
                start_dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                return (end_dt - start_dt).total_seconds()
        except Exception:
            pass
        return None
    
    def _calculate_rows_per_second(self, job_data: Dict, total_time: float) -> Optional[float]:
        """Calculate processing rate in rows per second"""
        try:
            successful_rows = job_data.get('successful_rows', 0)
            processing_time = self._calculate_processing_time(job_data)
            
            if processing_time and processing_time > 0:
                return successful_rows / processing_time
            elif total_time > 0:
                return successful_rows / total_time
        except Exception:
            pass
        return None
    
    async def test_single_file(self, file_path: str, endpoint: str, test_type: str) -> Dict:
        """Test a single file upload and return comprehensive results"""
        print(f"Testing {file_path} on {endpoint}...")
        
        try:
            # Step 1: Upload file
            upload_result = await self.upload_file(file_path, endpoint)
            
            if upload_result['status_code'] != 200:
                return {
                    'file_path': file_path,
                    'test_type': test_type,
                    'success': False,
                    'error': f"Upload failed with status {upload_result['status_code']}",
                    'upload_time': upload_result['upload_time']
                }
            
            # Step 2: Monitor job progress
            job_id = upload_result['response'].get('job_id')
            if not job_id:
                return {
                    'file_path': file_path,
                    'test_type': test_type,
                    'success': False,
                    'error': 'No job_id in upload response',
                    'upload_result': upload_result
                }
            
            progress_result = await self.monitor_job_progress(job_id)
            
            # Read file to get row count
            df = pd.read_excel(file_path)
            actual_rows = len(df)
            
            result = {
                'file_path': file_path,
                'test_type': test_type,
                'success': progress_result.get('status') == 'completed',
                'job_id': job_id,
                'actual_rows': actual_rows,
                'file_size_bytes': upload_result['file_size'],
                'upload_time_seconds': upload_result['upload_time'],
                'total_time_seconds': progress_result.get('total_time', 0),
                'processing_time_seconds': progress_result.get('processing_time'),
                'status_checks': progress_result.get('status_checks', 0),
                'rows_per_second': progress_result.get('rows_per_second'),
                'upload_response': upload_result['response'],
                'final_job_data': progress_result.get('job_data', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            if not result['success']:
                result['error'] = progress_result.get('error', 'Job failed')
            
            return result
            
        except Exception as e:
            return {
                'file_path': file_path,
                'test_type': test_type,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def run_performance_tests(self) -> Dict:
        """Run all performance tests"""
        print("=== BULK UPLOAD PERFORMANCE TESTING ===")
        print(f"Base URL: {self.base_url}")
        print(f"Bearer Token: {self.bearer_token[:20]}...")
        
        # Test files configuration
        test_files = [
            ('test_data/annual_test_10_rows.xlsx', '/api/v1/predictions/annual/bulk-upload-async', 'annual'),
            ('test_data/annual_test_20_rows.xlsx', '/api/v1/predictions/annual/bulk-upload-async', 'annual'),
            ('test_data/annual_test_50_rows.xlsx', '/api/v1/predictions/annual/bulk-upload-async', 'annual'),
            ('test_data/annual_test_100_rows.xlsx', '/api/v1/predictions/annual/bulk-upload-async', 'annual'),
            ('test_data/quarterly_test_10_rows.xlsx', '/api/v1/predictions/quarterly/bulk-upload-async', 'quarterly'),
            ('test_data/quarterly_test_20_rows.xlsx', '/api/v1/predictions/quarterly/bulk-upload-async', 'quarterly'),
            ('test_data/quarterly_test_50_rows.xlsx', '/api/v1/predictions/quarterly/bulk-upload-async', 'quarterly'),
            ('test_data/quarterly_test_100_rows.xlsx', '/api/v1/predictions/quarterly/bulk-upload-async', 'quarterly'),
        ]
        
        results = []
        
        for file_path, endpoint, test_type in test_files:
            result = await self.test_single_file(file_path, endpoint, test_type)
            results.append(result)
            
            # Print immediate result
            if result['success']:
                rows = result.get('actual_rows', 'N/A')
                total_time = result.get('total_time_seconds', 0)
                processing_time = result.get('processing_time_seconds', 0)
                rows_per_sec = result.get('rows_per_second', 0)
                
                print(f"✅ {Path(file_path).name}: {rows} rows, {total_time:.2f}s total, {processing_time:.2f}s processing, {rows_per_sec:.2f} rows/sec")
            else:
                print(f"❌ {Path(file_path).name}: {result.get('error', 'Unknown error')}")
            
            # Small delay between tests
            await asyncio.sleep(1)
        
        return {
            'test_results': results,
            'summary': self._generate_summary(results),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_summary(self, results: List[Dict]) -> Dict:
        """Generate performance summary statistics"""
        successful_results = [r for r in results if r['success']]
        
        if not successful_results:
            return {'error': 'No successful tests to analyze'}
        
        # Group by test type
        annual_results = [r for r in successful_results if r['test_type'] == 'annual']
        quarterly_results = [r for r in successful_results if r['test_type'] == 'quarterly']
        
        def analyze_results(test_results: List[Dict], test_type: str) -> Dict:
            if not test_results:
                return {}
            
            rows = [r['actual_rows'] for r in test_results if r.get('actual_rows')]
            total_times = [r['total_time_seconds'] for r in test_results if r.get('total_time_seconds')]
            processing_times = [r['processing_time_seconds'] for r in test_results if r.get('processing_time_seconds')]
            rows_per_sec = [r['rows_per_second'] for r in test_results if r.get('rows_per_second')]
            
            return {
                'test_count': len(test_results),
                'row_counts': rows,
                'avg_total_time': statistics.mean(total_times) if total_times else 0,
                'avg_processing_time': statistics.mean(processing_times) if processing_times else 0,
                'avg_rows_per_second': statistics.mean(rows_per_sec) if rows_per_sec else 0,
                'time_per_row': statistics.mean([t/r for t, r in zip(processing_times, rows) if r > 0]) if processing_times and rows else 0,
                'time_per_100_rows': None  # Will be calculated below
            }
        
        annual_analysis = analyze_results(annual_results, 'annual')
        quarterly_analysis = analyze_results(quarterly_results, 'quarterly')
        
        # Calculate time per 100 rows
        if annual_analysis.get('time_per_row'):
            annual_analysis['time_per_100_rows'] = annual_analysis['time_per_row'] * 100
        
        if quarterly_analysis.get('time_per_row'):
            quarterly_analysis['time_per_100_rows'] = quarterly_analysis['time_per_row'] * 100
        
        return {
            'total_tests': len(results),
            'successful_tests': len(successful_results),
            'failed_tests': len(results) - len(successful_results),
            'annual_analysis': annual_analysis,
            'quarterly_analysis': quarterly_analysis
        }

def save_results(results: Dict, filename: str = 'performance_test_results.json'):
    """Save test results to JSON file"""
    with open(filename, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"Results saved to {filename}")

def print_detailed_report(results: Dict):
    """Print detailed performance report"""
    print("\n" + "="*80)
    print("DETAILED PERFORMANCE REPORT")
    print("="*80)
    
    summary = results['summary']
    
    print(f"Test Summary:")
    print(f"  Total Tests: {summary['total_tests']}")
    print(f"  Successful: {summary['successful_tests']}")
    print(f"  Failed: {summary['failed_tests']}")
    print(f"  Success Rate: {(summary['successful_tests']/summary['total_tests']*100):.1f}%")
    
    if 'annual_analysis' in summary and summary['annual_analysis']:
        print(f"\n📊 ANNUAL PREDICTIONS PERFORMANCE:")
        annual = summary['annual_analysis']
        print(f"  Tests Completed: {annual.get('test_count', 0)}")
        print(f"  Average Processing Time: {annual.get('avg_processing_time', 0):.2f} seconds")
        print(f"  Average Rows/Second: {annual.get('avg_rows_per_second', 0):.2f}")
        print(f"  Time per Row: {annual.get('time_per_row', 0):.4f} seconds")
        print(f"  Time per 100 Rows: {annual.get('time_per_100_rows', 0):.2f} seconds")
    
    if 'quarterly_analysis' in summary and summary['quarterly_analysis']:
        print(f"\n📊 QUARTERLY PREDICTIONS PERFORMANCE:")
        quarterly = summary['quarterly_analysis']
        print(f"  Tests Completed: {quarterly.get('test_count', 0)}")
        print(f"  Average Processing Time: {quarterly.get('avg_processing_time', 0):.2f} seconds")
        print(f"  Average Rows/Second: {quarterly.get('avg_rows_per_second', 0):.2f}")
        print(f"  Time per Row: {quarterly.get('time_per_row', 0):.4f} seconds")
        print(f"  Time per 100 Rows: {quarterly.get('time_per_100_rows', 0):.2f} seconds")
    
    print(f"\n📈 EXTRAPOLATION FOR LARGER FILES:")
    if summary.get('annual_analysis', {}).get('time_per_row'):
        time_per_row = summary['annual_analysis']['time_per_row']
        print(f"Annual Predictions - Estimated times:")
        for n in [500, 1000, 2000, 5000, 10000]:
            estimated_time = time_per_row * n
            print(f"  {n:5d} rows: ~{estimated_time/60:.1f} minutes ({estimated_time:.1f} seconds)")
    
    if summary.get('quarterly_analysis', {}).get('time_per_row'):
        time_per_row = summary['quarterly_analysis']['time_per_row']
        print(f"Quarterly Predictions - Estimated times:")
        for n in [500, 1000, 2000, 5000, 10000]:
            estimated_time = time_per_row * n
            print(f"  {n:5d} rows: ~{estimated_time/60:.1f} minutes ({estimated_time:.1f} seconds)")

async def main():
    # Configuration
    BASE_URL = input("Enter your Railway deployment URL (e.g., https://your-app.railway.app): ").strip()
    BEARER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwNjhlOTNhYy03ZDBkLTQ0MzctOGRiZC0yYWExZGVhNjRlNzEiLCJleHAiOjE3NTg4NDg0MTF9.ffokqOiVaj0N1XjslRBjk5W2zGR2W6xexU1OHYlgSfA"
    
    if not BASE_URL:
        print("Error: Base URL is required")
        return
    
    # Run tests
    async with BulkUploadPerformanceTester(BASE_URL, BEARER_TOKEN) as tester:
        results = await tester.run_performance_tests()
    
    # Save and display results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_filename = f"performance_test_results_{timestamp}.json"
    save_results(results, results_filename)
    print_detailed_report(results)

if __name__ == "__main__":
    asyncio.run(main())
