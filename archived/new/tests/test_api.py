#!/usr/bin/env python3
"""
Test script for the multi-tenant API endpoints
"""

import requests
import json
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:8000/api"

class APITester:
    def __init__(self):
        self.token = None
        self.headers = {}
        
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
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
    
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
        print(f"Response: {result}")
        
        if response.status_code == 200:
            self.set_auth_token(result["access_token"])
            return True
        return False
    
    def test_get_profile(self):
        """Test getting user profile."""
        print("\n👤 Testing Get User Profile...")
        
        response = requests.get(f"{BASE_URL}/auth/me", headers=self.headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
    
    def test_create_organization(self):
        """Test creating an organization (should fail for regular user)."""
        print("\n🏢 Testing Create Organization...")
        
        org_data = {
            "name": "Test Organization",
            "description": "A test organization",
            "max_users": 50
        }
        
        response = requests.post(f"{BASE_URL}/organizations", json=org_data, headers=self.headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        # This should fail for regular users (403 Forbidden)
        return response.status_code == 403
    
    def test_list_organizations(self):
        """Test listing organizations."""
        print("\n📋 Testing List Organizations...")
        
        response = requests.get(f"{BASE_URL}/organizations", headers=self.headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
    
    def test_list_users(self):
        """Test listing users."""
        print("\n👥 Testing List Users...")
        
        response = requests.get(f"{BASE_URL}/users", headers=self.headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        return response.status_code == 200
    
    def run_all_tests(self):
        """Run all API tests."""
        print("🚀 Starting Multi-Tenant API Tests")
        print("=" * 50)
        
        tests = [
            ("User Registration", self.test_user_registration),
            ("User Login", self.test_user_login),
            ("Get Profile", self.test_get_profile),
            ("Create Organization", self.test_create_organization),
            ("List Organizations", self.test_list_organizations),
            ("List Users", self.test_list_users),
        ]
        
        results = []
        for test_name, test_func in tests:
            try:
                result = test_func()
                results.append((test_name, "✅ PASS" if result else "❌ FAIL"))
            except Exception as e:
                results.append((test_name, f"💥 ERROR: {str(e)}"))
        
        print("\n" + "=" * 50)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 50)
        
        for test_name, result in results:
            print(f"{test_name:<25} {result}")
        
        print("\n✨ API testing completed!")

if __name__ == "__main__":
    tester = APITester()
    tester.run_all_tests()
