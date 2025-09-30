"""
Concurrent Load Testing for Authentication APIs
"""
import asyncio
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BASE_URL, TEST_CONFIG
from utils.test_utils import APITester, ReportGenerator, print_test_header
from auth_apis.test_auth_performance import AuthAPITester

class ConcurrentAuthTester:
    """Concurrent load testing for auth APIs"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []
    
    async def concurrent_user_simulation(self, user_id: int, iterations: int = 5):
        """Simulate a single user's auth flow"""
        
        auth_tester = AuthAPITester(self.base_url)
        user_results = []
        
        try:
            # Generate unique user data for this simulated user
            user_data = await auth_tester.generate_test_user_data(f"concurrent_{user_id}")
            
            async with APITester(self.base_url) as tester:
                
                # 1. Register user
                reg_result = await tester.make_request(
                    method="POST",
                    endpoint="/api/v1/auth/register",
                    data=user_data
                )
                user_results.append(reg_result)
                
                if reg_result.success:
                    # 2. Login multiple times
                    for i in range(iterations):
                        login_data = {
                            "email": user_data["email"],
                            "password": user_data["password"]
                        }
                        
                        login_result = await tester.make_request(
                            method="POST",
                            endpoint="/api/v1/auth/login",
                            data=login_data
                        )
                        user_results.append(login_result)
                        
                        # 3. Logout
                        logout_result = await tester.make_request(
                            method="POST",
                            endpoint="/api/v1/auth/logout"
                        )
                        user_results.append(logout_result)
                        
                        # Small delay between login cycles
                        await asyncio.sleep(0.1)
                
                return user_results
                
        except Exception as e:
            print(f"Error in user {user_id} simulation: {e}")
            return user_results
    
    async def run_concurrent_load_test(self, concurrent_users: int = 10, iterations_per_user: int = 3):
        """Run concurrent load test with multiple simulated users"""
        
        print_test_header(f"CONCURRENT LOAD TEST - {concurrent_users} USERS")
        
        print(f"Simulating {concurrent_users} concurrent users")
        print(f"Each user will perform {iterations_per_user} login/logout cycles")
        print(f"Total expected API calls: ~{concurrent_users * (1 + iterations_per_user * 2)}")
        
        start_time = time.time()
        
        # Create tasks for concurrent users
        tasks = [
            self.concurrent_user_simulation(user_id, iterations_per_user)
            for user_id in range(concurrent_users)
        ]
        
        # Run all tasks concurrently
        print(f"\nStarting concurrent test at {datetime.now()}")
        all_user_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        # Flatten results
        all_results = []
        successful_users = 0
        
        for user_results in all_user_results:
            if isinstance(user_results, Exception):
                print(f"User simulation failed: {user_results}")
                continue
                
            successful_users += 1
            all_results.extend(user_results)
        
        # Analyze results by endpoint
        endpoints = ["/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/logout"]
        
        print(f"\n{'-'*80}")
        print(f"CONCURRENT LOAD TEST RESULTS")
        print(f"{'-'*80}")
        print(f"Test Duration: {total_duration:.2f} seconds")
        print(f"Successful Users: {successful_users}/{concurrent_users}")
        print(f"Total API Calls: {len(all_results)}")
        print(f"Overall Throughput: {len(all_results)/total_duration:.2f} requests/second")
        
        # Analyze each endpoint
        for endpoint in endpoints:
            endpoint_results = [r for r in all_results if r.endpoint == endpoint]
            if not endpoint_results:
                continue
            
            successful = [r for r in endpoint_results if r.success]
            response_times = [r.response_time for r in successful]
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
                success_rate = len(successful) / len(endpoint_results) * 100
                
                print(f"\n{endpoint}:")
                print(f"  Total Requests: {len(endpoint_results)}")
                print(f"  Success Rate: {success_rate:.1f}%")
                print(f"  Avg Response Time: {avg_time:.2f}ms")
                print(f"  Min Response Time: {min_time:.2f}ms")
                print(f"  Max Response Time: {max_time:.2f}ms")
                print(f"  Throughput: {len(successful)/(total_duration):.2f} req/sec")
        
        # Check for errors
        failed_results = [r for r in all_results if not r.success]
        if failed_results:
            print(f"\n{'-'*40}")
            print(f"ERRORS SUMMARY ({len(failed_results)} failures):")
            
            # Group errors by type
            error_counts = {}
            for result in failed_results:
                error_key = f"{result.status_code}: {result.error[:50] if result.error else 'Unknown'}"
                error_counts[error_key] = error_counts.get(error_key, 0) + 1
            
            for error, count in error_counts.items():
                print(f"  {error} (x{count})")
        
        return all_results
    
    async def run_stress_test(self, max_users: int = 50, ramp_up_time: int = 10):
        """Run stress test with gradually increasing load"""
        
        print_test_header(f"STRESS TEST - RAMPING UP TO {max_users} USERS")
        
        user_levels = [5, 10, 20, 30, max_users]
        
        for user_count in user_levels:
            print(f"\n{'='*60}")
            print(f"Testing with {user_count} concurrent users")
            print(f"{'='*60}")
            
            # Run concurrent test at this level
            results = await self.run_concurrent_load_test(user_count, 2)
            
            # Brief pause between levels
            print(f"Waiting {ramp_up_time//2} seconds before next level...")
            await asyncio.sleep(ramp_up_time // 2)
        
        print_test_header("STRESS TEST COMPLETED")

async def main():
    """Main function for concurrent testing"""
    
    print("Starting Concurrent Load Testing for Authentication APIs")
    print(f"Target API: {BASE_URL}")
    
    # Check server availability
    try:
        async with APITester(BASE_URL) as tester:
            result = await tester.make_request("GET", "/")
            if not result.success:
                print(f"✗ API server is not responding properly")
                return
    except Exception as e:
        print(f"✗ Cannot connect to API server: {e}")
        return
    
    concurrent_tester = ConcurrentAuthTester(BASE_URL)
    
    # Test with different concurrent user levels
    test_levels = [5, 10, 20]
    
    for level in test_levels:
        print(f"\n{'#'*80}")
        print(f"TESTING WITH {level} CONCURRENT USERS")
        print(f"{'#'*80}")
        
        await concurrent_tester.run_concurrent_load_test(
            concurrent_users=level,
            iterations_per_user=3
        )
        
        # Brief pause between test levels
        print(f"\nCooling down for 5 seconds before next test level...")
        await asyncio.sleep(5)
    
    # Optional: Run stress test
    print(f"\n{'#'*80}")
    print("STARTING STRESS TEST")
    print(f"{'#'*80}")
    await concurrent_tester.run_stress_test(max_users=30, ramp_up_time=10)

if __name__ == "__main__":
    asyncio.run(main())
