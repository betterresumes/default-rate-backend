"""
Quick diagnostic test for auth registration
"""
import asyncio
import httpx
import json
from datetime import datetime

async def test_registration_debug():
    """Debug registration issues"""
    
    base_url = "http://localhost:8000"
    
    # Test data that worked with curl
    test_data = {
        "email": f"debug_{int(datetime.now().timestamp())}@testdomain.local",
        "password": "TestPass123!",
        "username": f"debuguser_{int(datetime.now().timestamp())}",
        "full_name": "Debug Test User"
    }
    
    print(f"Testing registration with data:")
    print(json.dumps(test_data, indent=2))
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.post(
                f"{base_url}/api/v1/auth/register",
                json=test_data
            )
            
            print(f"\nResponse Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                print(f"Response Body:")
                print(json.dumps(response_json, indent=2))
            except:
                print(f"Response Text: {response.text}")
                
            if response.status_code == 201:
                print("✅ Registration successful!")
                return test_data
            else:
                print("❌ Registration failed!")
                return None
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
            return None

async def main():
    result = await test_registration_debug()
    
    if result:
        print(f"\n🔄 Testing login with registered user...")
        
        login_data = {
            "email": result["email"],
            "password": result["password"]
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                "http://localhost:8000/api/v1/auth/login",
                json=login_data
            )
            
            print(f"Login Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Login successful!")
                login_result = response.json()
                print(f"Token received: {login_result.get('access_token', 'No token')[:20]}...")
            else:
                print(f"❌ Login failed: {response.text}")

if __name__ == "__main__":
    asyncio.run(main())
