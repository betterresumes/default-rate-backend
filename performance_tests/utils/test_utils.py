"""
Utilities for Performance Testing
"""
import time
import asyncio
import json
import csv
import statistics
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import httpx
import psutil
import os
from colorama import Fore, Style, init

init(autoreset=True)

@dataclass
class TestResult:
    """Single test result"""
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error: Optional[str] = None
    timestamp: datetime = None
    memory_usage: float = 0.0
    cpu_usage: float = 0.0

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

@dataclass
class TestSession:
    """Test session aggregated results"""
    endpoint: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    p95_response_time: float
    p99_response_time: float
    throughput: float  # requests per second
    error_rate: float
    errors: List[str]
    start_time: datetime
    end_time: datetime

class PerformanceMonitor:
    """Monitor system performance during tests"""
    
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
    def get_current_stats(self):
        """Get current system stats"""
        memory_mb = self.process.memory_info().rss / 1024 / 1024
        cpu_percent = self.process.cpu_percent()
        
        return {
            'memory_mb': memory_mb,
            'cpu_percent': cpu_percent,
            'memory_growth': memory_mb - self.initial_memory
        }

class APITester:
    """Base API testing utility"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = None
        self.monitor = PerformanceMonitor()
        self.results: List[TestResult] = []
        
    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            timeout=self.timeout,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()
    
    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        auth_token: Optional[str] = None
    ) -> TestResult:
        """Make a single API request and measure performance"""
        
        url = f"{self.base_url}{endpoint}"
        if headers is None:
            headers = {}
            
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
            
        stats_before = self.monitor.get_current_stats()
        start_time = time.perf_counter()
        
        try:
            if method.upper() == "GET":
                response = await self.session.get(url, headers=headers, params=data)
            elif method.upper() == "POST":
                response = await self.session.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = await self.session.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = await self.session.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000  # Convert to milliseconds
            
            stats_after = self.monitor.get_current_stats()
            
            result = TestResult(
                endpoint=endpoint,
                method=method.upper(),
                status_code=response.status_code,
                response_time=response_time,
                success=200 <= response.status_code < 300,
                timestamp=datetime.utcnow(),
                memory_usage=stats_after['memory_mb'],
                cpu_usage=stats_after['cpu_percent']
            )
            
            if not result.success:
                try:
                    error_detail = response.json().get('detail', 'Unknown error')
                except:
                    error_detail = response.text[:200]
                result.error = f"HTTP {response.status_code}: {error_detail}"
                
            self.results.append(result)
            return result
            
        except Exception as e:
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            
            result = TestResult(
                endpoint=endpoint,
                method=method.upper(),
                status_code=0,
                response_time=response_time,
                success=False,
                error=str(e),
                timestamp=datetime.utcnow()
            )
            
            self.results.append(result)
            return result

    def analyze_results(self, endpoint_filter: Optional[str] = None) -> TestSession:
        """Analyze test results for a specific endpoint"""
        
        if endpoint_filter:
            filtered_results = [r for r in self.results if r.endpoint == endpoint_filter]
        else:
            filtered_results = self.results
            
        if not filtered_results:
            raise ValueError("No results to analyze")
            
        successful_results = [r for r in filtered_results if r.success]
        failed_results = [r for r in filtered_results if not r.success]
        
        response_times = [r.response_time for r in successful_results]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            sorted_times = sorted(response_times)
            p95_index = int(0.95 * len(sorted_times))
            p99_index = int(0.99 * len(sorted_times))
            
            p95_response_time = sorted_times[p95_index] if p95_index < len(sorted_times) else max_response_time
            p99_response_time = sorted_times[p99_index] if p99_index < len(sorted_times) else max_response_time
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = p99_response_time = 0
            
        start_time = min(r.timestamp for r in filtered_results)
        end_time = max(r.timestamp for r in filtered_results)
        duration = (end_time - start_time).total_seconds()
        
        throughput = len(successful_results) / duration if duration > 0 else 0
        error_rate = len(failed_results) / len(filtered_results) * 100
        
        errors = [r.error for r in failed_results if r.error]
        
        return TestSession(
            endpoint=endpoint_filter or "ALL",
            total_requests=len(filtered_results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time=avg_response_time,
            min_response_time=min_response_time,
            max_response_time=max_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            throughput=throughput,
            error_rate=error_rate,
            errors=errors,
            start_time=start_time,
            end_time=end_time
        )

class ReportGenerator:
    """Generate performance test reports"""
    
    @staticmethod
    def print_summary(session: TestSession, threshold: Optional[float] = None):
        """Print a formatted summary of test results"""
        
        status_color = Fore.GREEN if session.error_rate < 5 else Fore.YELLOW if session.error_rate < 15 else Fore.RED
        
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}Performance Test Results: {session.endpoint}")
        print(f"{Fore.CYAN}{'='*60}")
        
        print(f"{Fore.WHITE}Total Requests:     {session.total_requests}")
        print(f"{Fore.GREEN}Successful:         {session.successful_requests}")
        print(f"{Fore.RED}Failed:             {session.failed_requests}")
        print(f"{status_color}Error Rate:         {session.error_rate:.2f}%")
        print(f"{Fore.WHITE}Throughput:         {session.throughput:.2f} req/sec")
        
        print(f"\n{Fore.YELLOW}Response Times (ms):")
        print(f"{Fore.WHITE}Average:            {session.avg_response_time:.2f}")
        print(f"{Fore.WHITE}Min:                {session.min_response_time:.2f}")
        print(f"{Fore.WHITE}Max:                {session.max_response_time:.2f}")
        print(f"{Fore.WHITE}95th Percentile:    {session.p95_response_time:.2f}")
        print(f"{Fore.WHITE}99th Percentile:    {session.p99_response_time:.2f}")
        
        if threshold:
            threshold_color = Fore.GREEN if session.avg_response_time <= threshold else Fore.RED
            print(f"{threshold_color}Threshold ({threshold}ms): {'✓ PASS' if session.avg_response_time <= threshold else '✗ FAIL'}")
        
        if session.errors:
            print(f"\n{Fore.RED}Errors:")
            for error in set(session.errors):
                count = session.errors.count(error)
                print(f"{Fore.RED}  - {error} (x{count})")
        
        duration = (session.end_time - session.start_time).total_seconds()
        print(f"\n{Fore.CYAN}Duration: {duration:.2f} seconds")
        print(f"{Fore.CYAN}{'='*60}")

    @staticmethod
    def save_json_report(session: TestSession, filepath: str):
        """Save results to JSON file"""
        
        data = {
            'endpoint': session.endpoint,
            'summary': {
                'total_requests': session.total_requests,
                'successful_requests': session.successful_requests,
                'failed_requests': session.failed_requests,
                'error_rate': session.error_rate,
                'throughput': session.throughput
            },
            'response_times': {
                'average': session.avg_response_time,
                'min': session.min_response_time,
                'max': session.max_response_time,
                'p95': session.p95_response_time,
                'p99': session.p99_response_time
            },
            'errors': session.errors,
            'test_period': {
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat()
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def save_csv_report(results: List[TestResult], filepath: str):
        """Save individual test results to CSV"""
        
        with open(filepath, 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'endpoint', 'method', 'status_code', 'response_time', 'success', 'error', 'memory_usage', 'cpu_usage']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for result in results:
                writer.writerow({
                    'timestamp': result.timestamp.isoformat(),
                    'endpoint': result.endpoint,
                    'method': result.method,
                    'status_code': result.status_code,
                    'response_time': result.response_time,
                    'success': result.success,
                    'error': result.error or '',
                    'memory_usage': result.memory_usage,
                    'cpu_usage': result.cpu_usage
                })

def print_test_header(test_name: str):
    """Print a formatted test header"""
    print(f"\n{Fore.MAGENTA}{'='*80}")
    print(f"{Fore.MAGENTA}{test_name.center(80)}")
    print(f"{Fore.MAGENTA}{'='*80}")

async def wait_between_requests(delay: float = 0.1):
    """Add delay between requests to avoid overwhelming the server"""
    await asyncio.sleep(delay)
