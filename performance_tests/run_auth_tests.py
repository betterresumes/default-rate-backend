#!/usr/bin/env python3
"""
Authentication API Performance Test Runner
"""
import asyncio
import sys
import os
import argparse
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import BASE_URL, TEST_CONFIG
from auth_apis.test_auth_performance import AuthAPITester
from auth_apis.test_concurrent_auth import ConcurrentAuthTester
from utils.test_utils import print_test_header

async def run_basic_tests():
    """Run basic sequential auth API tests"""
    tester = AuthAPITester(BASE_URL)
    await tester.run_all_auth_tests()

async def run_concurrent_tests(users: int = 10):
    """Run concurrent auth API tests"""
    tester = ConcurrentAuthTester(BASE_URL)
    await tester.run_concurrent_load_test(users, 3)

async def run_stress_tests(max_users: int = 30):
    """Run stress tests"""
    tester = ConcurrentAuthTester(BASE_URL)
    await tester.run_stress_test(max_users)

async def run_full_suite():
    """Run complete test suite"""
    print_test_header("FULL AUTH API PERFORMANCE TEST SUITE")
    
    print("1. Running basic performance tests...")
    await run_basic_tests()
    
    print("\n2. Running concurrent load tests...")
    await run_concurrent_tests(10)
    
    print("\n3. Running stress tests...")
    await run_stress_tests(20)
    
    print_test_header("FULL TEST SUITE COMPLETED")

def main():
    parser = argparse.ArgumentParser(description="Auth API Performance Testing")
    parser.add_argument('--test-type', choices=['basic', 'concurrent', 'stress', 'full'], 
                       default='basic', help='Type of test to run')
    parser.add_argument('--users', type=int, default=10, 
                       help='Number of concurrent users for load tests')
    parser.add_argument('--max-users', type=int, default=30,
                       help='Maximum users for stress test')
    parser.add_argument('--url', default=BASE_URL,
                       help='API base URL')
    
    args = parser.parse_args()
    
    # Update config if URL is provided
    if args.url != BASE_URL:
        import config
        config.BASE_URL = args.url
    
    print(f"""
Authentication API Performance Testing
=====================================
Test Type: {args.test_type}
API URL: {args.url}
Concurrent Users: {args.users}
Max Users (stress): {args.max_users}
Start Time: {datetime.now()}
=====================================
    """)
    
    if args.test_type == 'basic':
        asyncio.run(run_basic_tests())
    elif args.test_type == 'concurrent':
        asyncio.run(run_concurrent_tests(args.users))
    elif args.test_type == 'stress':
        asyncio.run(run_stress_tests(args.max_users))
    elif args.test_type == 'full':
        asyncio.run(run_full_suite())

if __name__ == "__main__":
    main()
