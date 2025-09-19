#!/usr/bin/env python3
"""
Test the clean multi-tenant API endpoints
"""

import requests
import json
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:8001/api"

class MultiTenantAPITester:
    def __init__(self):
        self.token = None
        self.headers = {}
        self.user_id = None
        
    def set_auth_token(self, token):
        """Set authentication token for subsequent requests."""
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def test_user_registration(self):
        """Test user registration."""
        print("\n🧪 Testing User Registration...")
        
        user_data = {
            "email": "testuser@example.com",
            "username": "testuser",
            "full_name": "Test User",
            "password": "testpass123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200:
            self.user_id = result.get("id")
            return True
        return False
    
    def test_user_login(self):
        """Test user login."""
        print("\n🔐 Testing User Login...")
        
        login_data = {
            "email": "testuser@example.com",
            "password": "testpass123"
        }
        
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        if response.status_code == 200:
            self.set_auth_token(result["access_token"])
            return True
        return False
    
    def test_get_profile(self):
        """Test getting user profile."""
        print("\n👤 Testing Get User Profile...")
        
        response = requests.get(f"{BASE_URL}/auth/me", headers=self.headers)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return response.status_code == 200
    
    def test_create_tenant_as_user(self):
        """Test creating a tenant as regular user (should fail)."""
        print("\n🏢 Testing Create Tenant as Regular User...")
        
        tenant_data = {
            "name": "Test Enterprise",
            "description": "A test enterprise tenant",
            "domain": "testenterprise.com"
        }
        
        response = requests.post(f"{BASE_URL}/tenants", json=tenant_data, headers=self.headers)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Should fail with 403 Forbidden
        return response.status_code == 403
    
    def test_create_organization_as_user(self):
        """Test creating an organization as regular user (should fail)."""
        print("\n🏪 Testing Create Organization as Regular User...")
        
        org_data = {
            "name": "Test Organization",
            "description": "A test organization",
            "max_users": 50
        }
        
        response = requests.post(f"{BASE_URL}/organizations", json=org_data, headers=self.headers)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Should fail with 403 Forbidden
        return response.status_code == 403
    
    def test_list_organizations_empty(self):
        """Test listing organizations (should be empty for new user)."""
        print("\n📋 Testing List Organizations (Empty)...")
        
        response = requests.get(f"{BASE_URL}/organizations", headers=self.headers)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Should succeed but return empty list
        return response.status_code == 200 and result.get("total", 0) == 0
    
    def test_list_users(self):
        """Test listing users (should only see self)."""
        print("\n👥 Testing List Users (Self Only)...")
        
        response = requests.get(f"{BASE_URL}/users", headers=self.headers)
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        # Should succeed and return only current user
        return (response.status_code == 200 and 
                result.get("total", 0) == 1 and
                len(result.get("users", [])) == 1)
    
    def test_health_check(self):
        """Test health check endpoint."""
        print("\n❤️  Testing Health Check...")
        
        response = requests.get("http://localhost:8001/health")
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        
        return response.status_code == 200 and result.get("status") == "healthy"
    
    def run_all_tests(self):
        """Run all API tests."""
        print("🚀 Starting Clean Multi-Tenant API Tests")
        print("=" * 60)
        
        tests = [
            ("Health Check", self.test_health_check),
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Get Profile", self.test_get_profile),
            ("Create Tenant (Should Fail)", self.test_create_tenant_as_user),
            ("Create Organization (Should Fail)", self.test_create_organization_as_user),
            ("List Organizations (Empty)", self.test_list_organizations_empty),
            ("List Users (Self Only)", self.test_list_users),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                print(f"\n⏳ Running: {test_name}")
                result = test_func()
                status = "✅ PASS" if result else "❌ FAIL"
                results.append((test_name, status))
                print(f"Result: {status}")
            except Exception as e:
                error_msg = f"💥 ERROR: {str(e)}"
                results.append((test_name, error_msg))
                print(f"Result: {error_msg}")
        
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed = 0
        for test_name, result in results:
            print(f"{test_name:<35} {result}")
            if "PASS" in result:
                passed += 1
        
        print(f"\n✨ Tests completed: {passed}/{len(tests)} passed")
        
        if passed == len(tests):
            print("🎉 All tests passed! Multi-tenant API is working correctly!")
        else:
            print("⚠️  Some tests failed. Check the logs above.")

if __name__ == "__main__":
    tester = MultiTenantAPITester()
    tester.run_all_tests()
