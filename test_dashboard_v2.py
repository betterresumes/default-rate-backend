#!/usr/bin/env python3
"""
Test script for the enhanced Dashboard API v2

This script tests the new POST dashboard endpoint and validates performance.
Run this after starting your FastAPI server.
"""

import requests
import time
import json

# Configuration
BASE_URL = "http://localhost:8000/api/v1/predictions"
# You'll need to get a valid JWT token from your authentication endpoint
AUTH_TOKEN = "your-jwt-token-here"

headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}",
    "Content-Type": "application/json"
}

def test_stats_endpoint():
    """Test the /stats endpoint (now available to all users)"""
    print("🧪 Testing /stats endpoint...")
    
    start_time = time.time()
    try:
        response = requests.get(f"{BASE_URL}/stats", headers=headers)
        end_time = time.time()
        
        print(f"⏱️  Response time: {end_time - start_time:.2f} seconds")
        print(f"📊 Status code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success! Found {data['summary']['total_predictions']} total predictions")
            return True
        else:
            print(f"❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_dashboard_endpoint():
    """Test the new POST /dashboard endpoint"""
    print("\\n🧪 Testing /dashboard endpoint...")
    
    # Test different request payloads
    test_cases = [
        {
            "name": "Basic dashboard with platform stats",
            "payload": {"include_platform_stats": True}
        },
        {
            "name": "Dashboard without platform stats", 
            "payload": {"include_platform_stats": False}
        },
        {
            "name": "Custom scope dashboard",
            "payload": {
                "include_platform_stats": True,
                "custom_scope": "organization"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\\n🔍 Testing: {test_case['name']}")
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/dashboard", 
                headers=headers,
                json=test_case["payload"]
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            print(f"⏱️  Response time: {response_time:.2f} seconds")
            print(f"📊 Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Success! Scope: {data.get('scope')}")
                print(f"📈 Companies: {data.get('total_companies')}")
                print(f"📊 Predictions: {data.get('total_predictions')}")
                
                if data.get('platform_statistics'):
                    platform = data['platform_statistics']
                    print(f"🌐 Platform total: {platform.get('total_predictions')} predictions")
                
                # Check if performance target is met
                if response_time > 15:
                    print(f"⚠️  WARNING: Response time ({response_time:.2f}s) exceeds 15s target!")
                else:
                    print(f"🚀 EXCELLENT: Response time under 15s target!")
                    
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

def performance_benchmark():
    """Run multiple requests to benchmark performance"""
    print("\\n🏃‍♂️ Running performance benchmark...")
    
    times = []
    success_count = 0
    
    for i in range(5):
        print(f"Request {i+1}/5...", end=" ")
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/dashboard",
                headers=headers,
                json={"include_platform_stats": True}
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            times.append(response_time)
            
            if response.status_code == 200:
                success_count += 1
                print(f"✅ {response_time:.2f}s")
            else:
                print(f"❌ Failed ({response.status_code})")
                
        except Exception as e:
            print(f"❌ Error: {e}")
    
    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\\n📊 Performance Summary:")
        print(f"   Success rate: {success_count}/5 ({success_count*20}%)")
        print(f"   Average time: {avg_time:.2f}s")
        print(f"   Min time: {min_time:.2f}s") 
        print(f"   Max time: {max_time:.2f}s")
        
        if avg_time <= 15:
            print(f"🎉 PERFORMANCE TARGET MET! Average under 15s")
        else:
            print(f"⚠️  Performance target missed. Consider database indexing.")

def main():
    """Main test runner"""
    print("🚀 Dashboard API v2 Test Suite")
    print("=" * 50)
    
    # Check if auth token is configured
    if AUTH_TOKEN == "your-jwt-token-here":
        print("⚠️  Please update AUTH_TOKEN in this script with a valid JWT token")
        print("💡 You can get a token by calling your /auth/login endpoint")
        return
    
    # Run tests
    print("\\n1. Testing Stats Endpoint")
    test_stats_endpoint()
    
    print("\\n2. Testing Dashboard Endpoint") 
    test_dashboard_endpoint()
    
    print("\\n3. Performance Benchmark")
    performance_benchmark()
    
    print("\\n🏁 Test suite complete!")
    print("\\n💡 Next steps:")
    print("   - Verify all tests passed")
    print("   - Check performance meets <15s target")
    print("   - Create database indexes if needed")
    print("   - Monitor production performance")

if __name__ == "__main__":
    main()
