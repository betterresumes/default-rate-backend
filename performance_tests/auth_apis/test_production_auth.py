"""
Clean Authentication API Performance Tests - Production Ready
"""
import asyncio
import os
import sys
from datetime import datetime
from faker import Faker
import random
import time
import uuid

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BASE_URL, TEST_CONFIG, AUTH_TEST_DATA, PERFORMANCE_THRESHOLDS
from utils.test_utils import APITester, ReportGenerator, print_test_header, wait_between_requests

fake = Faker()

class ProductionAuthTester:
    """Production-ready authentication API tester"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())[:8]  # Unique session ID
        self.test_results = {
            'register': [],
            'login': [], 
            'logout': [],
            'invalid_login': [],
            'validation_errors': []
        }
        
    def generate_unique_user_data(self, test_type: str, index: int = 0) -> dict:
        """Generate truly unique user data"""
        timestamp = int(time.time() * 1000)  # Millisecond timestamp
        unique_id = f"{self.session_id}_{test_type}_{index}_{timestamp}_{random.randint(1000, 9999)}"
        
        return {
            "email": f"perftest_{unique_id}@testdomain.local",
            "password": "TestPass123!",
            "username": f"user_{unique_id}",
            "full_name": f"Test User {unique_id}"
        }
    
    async def test_single_registration(self, index: int) -> dict:
        """Test a single user registration"""
        user_data = self.generate_unique_user_data("reg", index)
        
        async with APITester(self.base_url, timeout=10) as tester:
            start_time = time.perf_counter()
            
            result = await tester.make_request(
                method="POST",
                endpoint="/api/v1/auth/register",
                data=user_data
            )
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            
            return {
                'success': result.success,
                'response_time': response_time,
                'status_code': result.status_code,
                'error': result.error,
                'user_data': user_data if result.success else None
            }
    
    async def test_single_login(self, user_data: dict) -> dict:
        """Test a single user login"""
        login_data = {
            "email": user_data["email"],
            "password": user_data["password"]
        }
        
        async with APITester(self.base_url, timeout=10) as tester:
            start_time = time.perf_counter()
            
            result = await tester.make_request(
                method="POST",
                endpoint="/api/v1/auth/login",
                data=login_data
            )
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            
            return {
                'success': result.success,
                'response_time': response_time,
                'status_code': result.status_code,
                'error': result.error
            }
    
    async def test_single_logout(self) -> dict:
        """Test a single logout"""
        async with APITester(self.base_url, timeout=5) as tester:
            start_time = time.perf_counter()
            
            result = await tester.make_request(
                method="POST",
                endpoint="/api/v1/auth/logout"
            )
            
            end_time = time.perf_counter()
            response_time = (end_time - start_time) * 1000
            
            return {
                'success': result.success,
                'response_time': response_time,
                'status_code': result.status_code,
                'error': result.error
            }
    
    async def run_registration_test(self, iterations: int = 5):
        """Run registration performance test"""
        print_test_header("REGISTRATION PERFORMANCE TEST (Production DB)")
        
        print(f"Testing {iterations} user registrations with production database...")
        print(f"Session ID: {self.session_id}")
        
        results = []
        successful_users = []
        
        for i in range(iterations):
            print(f"  Registration {i+1}/{iterations}...", end=" ")
            
            try:
                result = await self.test_single_registration(i)
                results.append(result)
                
                if result['success']:
                    successful_users.append(result['user_data'])
                    print(f"✓ {result['response_time']:.0f}ms")
                else:
                    print(f"✗ {result['response_time']:.0f}ms - {result['error'][:50]}")
                
                # Small delay to avoid overwhelming the server
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
                results.append({
                    'success': False,
                    'response_time': 0,
                    'error': str(e)
                })
        
        # Analyze results
        successful_results = [r for r in results if r['success']]
        response_times = [r['response_time'] for r in successful_results]
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\n📊 Registration Results:")
            print(f"  Total attempts: {len(results)}")
            print(f"  Successful: {len(successful_results)}")
            print(f"  Success rate: {len(successful_results)/len(results)*100:.1f}%")
            print(f"  Average time: {avg_time:.0f}ms")
            print(f"  Min time: {min_time:.0f}ms")
            print(f"  Max time: {max_time:.0f}ms")
            print(f"  Threshold: {PERFORMANCE_THRESHOLDS['auth']['register']}ms")
            
            if avg_time <= PERFORMANCE_THRESHOLDS['auth']['register']:
                print(f"  Status: ✅ PASS")
            else:
                print(f"  Status: ❌ FAIL (exceeds threshold)")
        
        self.test_results['register'] = results
        return successful_users
    
    async def run_login_test(self, registered_users: list, iterations_per_user: int = 3):
        """Run login performance test"""
        print_test_header("LOGIN PERFORMANCE TEST (Production DB)")
        
        if not registered_users:
            print("❌ No registered users available for login testing")
            return []
        
        # Use first registered user for login tests
        test_user = registered_users[0]
        print(f"Testing login with user: {test_user['email']}")
        print(f"Running {iterations_per_user} login attempts...")
        
        results = []
        
        for i in range(iterations_per_user):
            print(f"  Login {i+1}/{iterations_per_user}...", end=" ")
            
            try:
                result = await self.test_single_login(test_user)
                results.append(result)
                
                if result['success']:
                    print(f"✓ {result['response_time']:.0f}ms")
                else:
                    print(f"✗ {result['response_time']:.0f}ms - {result['error'][:50]}")
                
                await asyncio.sleep(0.2)
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
                results.append({
                    'success': False,
                    'response_time': 0,
                    'error': str(e)
                })
        
        # Analyze results
        successful_results = [r for r in results if r['success']]
        response_times = [r['response_time'] for r in successful_results]
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\n📊 Login Results:")
            print(f"  Total attempts: {len(results)}")
            print(f"  Successful: {len(successful_results)}")
            print(f"  Success rate: {len(successful_results)/len(results)*100:.1f}%")
            print(f"  Average time: {avg_time:.0f}ms")
            print(f"  Min time: {min_time:.0f}ms")
            print(f"  Max time: {max_time:.0f}ms")
            print(f"  Threshold: {PERFORMANCE_THRESHOLDS['auth']['login']}ms")
            
            if avg_time <= PERFORMANCE_THRESHOLDS['auth']['login']:
                print(f"  Status: ✅ PASS")
            else:
                print(f"  Status: ❌ FAIL (exceeds threshold)")
        
        self.test_results['login'] = results
        return results
    
    async def run_logout_test(self, iterations: int = 5):
        """Run logout performance test"""
        print_test_header("LOGOUT PERFORMANCE TEST (Production DB)")
        
        print(f"Testing {iterations} logout requests...")
        
        results = []
        
        for i in range(iterations):
            print(f"  Logout {i+1}/{iterations}...", end=" ")
            
            try:
                result = await self.test_single_logout()
                results.append(result)
                
                if result['success']:
                    print(f"✓ {result['response_time']:.0f}ms")
                else:
                    print(f"✗ {result['response_time']:.0f}ms - Status: {result['status_code']}")
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"✗ Error: {str(e)[:50]}")
                results.append({
                    'success': False,
                    'response_time': 0,
                    'error': str(e)
                })
        
        # Analyze results
        response_times = [r['response_time'] for r in results]
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            min_time = min(response_times)
            max_time = max(response_times)
            
            print(f"\n📊 Logout Results:")
            print(f"  Total attempts: {len(results)}")
            print(f"  Average time: {avg_time:.0f}ms")
            print(f"  Min time: {min_time:.0f}ms")
            print(f"  Max time: {max_time:.0f}ms")
            print(f"  Threshold: {PERFORMANCE_THRESHOLDS['auth']['logout']}ms")
            
            if avg_time <= PERFORMANCE_THRESHOLDS['auth']['logout']:
                print(f"  Status: ✅ PASS")
            else:
                print(f"  Status: ❌ FAIL (exceeds threshold)")
        
        self.test_results['logout'] = results
        return results
    
    async def run_invalid_login_test(self, iterations: int = 3):
        """Test invalid login performance"""
        print_test_header("INVALID LOGIN PERFORMANCE TEST")
        
        print(f"Testing {iterations} invalid login attempts...")
        
        results = []
        invalid_credentials = {
            "email": f"nonexistent_{self.session_id}@testdomain.local",
            "password": "WrongPassword123"
        }
        
        for i in range(iterations):
            print(f"  Invalid login {i+1}/{iterations}...", end=" ")
            
            async with APITester(self.base_url, timeout=10) as tester:
                start_time = time.perf_counter()
                
                result = await tester.make_request(
                    method="POST",
                    endpoint="/api/v1/auth/login",
                    data=invalid_credentials
                )
                
                end_time = time.perf_counter()
                response_time = (end_time - start_time) * 1000
                
                # For invalid login, we expect 401
                expected_failure = result.status_code == 401
                print(f"{'✓' if expected_failure else '?'} {response_time:.0f}ms (Status: {result.status_code})")
                
                results.append({
                    'response_time': response_time,
                    'status_code': result.status_code,
                    'expected_failure': expected_failure
                })
                
                await asyncio.sleep(0.1)
        
        # Analyze results
        response_times = [r['response_time'] for r in results]
        expected_failures = [r for r in results if r['expected_failure']]
        
        if response_times:
            avg_time = sum(response_times) / len(response_times)
            
            print(f"\n📊 Invalid Login Results:")
            print(f"  Total attempts: {len(results)}")
            print(f"  Expected failures (401): {len(expected_failures)}")
            print(f"  Average time: {avg_time:.0f}ms")
        
        return results
    
    async def run_all_tests(self):
        """Run all authentication tests"""
        print(f"""
{'='*80}
PRODUCTION AUTHENTICATION API PERFORMANCE TESTS
{'='*80}
API URL: {self.base_url}
Database: Production Neon PostgreSQL (with network latency)
Session ID: {self.session_id}
Start Time: {datetime.now()}
{'='*80}
        """)
        
        try:
            # 1. Registration Test
            registered_users = await self.run_registration_test(5)
            await asyncio.sleep(1)
            
            # 2. Login Test (if we have registered users)
            if registered_users:
                await self.run_login_test(registered_users, 3)
                await asyncio.sleep(1)
            
            # 3. Logout Test
            await self.run_logout_test(5)
            await asyncio.sleep(1)
            
            # 4. Invalid Login Test
            await self.run_invalid_login_test(3)
            
            # 5. Summary
            self.print_summary()
            
        except Exception as e:
            print(f"❌ Test suite error: {e}")
    
    def print_summary(self):
        """Print test summary"""
        print_test_header("PRODUCTION PERFORMANCE TEST SUMMARY")
        
        # Calculate overall statistics
        endpoints = ['register', 'login', 'logout']
        
        print(f"{'Endpoint':<15} {'Attempts':<10} {'Success':<10} {'Avg Time':<12} {'Threshold':<12} {'Status':<8}")
        print("-" * 75)
        
        for endpoint in endpoints:
            results = self.test_results.get(endpoint, [])
            if not results:
                continue
                
            successful = [r for r in results if r.get('success', True)]
            response_times = [r['response_time'] for r in successful if r['response_time'] > 0]
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                threshold = PERFORMANCE_THRESHOLDS['auth'].get(endpoint, 0)
                status = "✅ PASS" if avg_time <= threshold else "❌ FAIL"
                
                print(f"{endpoint:<15} {len(results):<10} {len(successful):<10} {avg_time:<12.0f} {threshold:<12} {status:<8}")
        
        print(f"\n{'='*75}")
        print(f"Test completed at {datetime.now()}")
        print(f"Session ID: {self.session_id}")

async def main():
    """Main function for production auth testing"""
    
    print("🚀 Starting Production Authentication API Performance Tests")
    print(f"Target API: {BASE_URL}")
    
    # Quick server check
    try:
        async with APITester(BASE_URL, timeout=5) as tester:
            result = await tester.make_request("GET", "/")
            if not result.success:
                print(f"❌ API server check failed: Status {result.status_code}")
                return
            print("✅ API server is responding")
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        return
    
    # Run tests
    tester = ProductionAuthTester(BASE_URL)
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
