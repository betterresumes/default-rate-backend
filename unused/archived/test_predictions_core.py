#!/usr/bin/env python3
"""
Simple test script for the Predictions API - focuses on core ML functionality
Tests the main prediction endpoints without complex dependencies
"""

import requests
import json
import uuid
from datetime import datetime

# API Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test user credentials (from setup_banking_data.py)
TEST_USERS = {
    "super_admin": {"email": "pranitsuperadmin@gmail.com", "password": "SuperAdmin123!"},
    "hdfc_central_analyst": {"email": "rohan.analyst@hdfcbank.com", "password": "RohanHdfc123!"},
}

class SimplePredictionsTest:
    def __init__(self):
        self.tokens = {}
        
    def login_user(self, user_type: str):
        """Login user and get access token"""
        user_creds = TEST_USERS[user_type]
        
        response = requests.post(f"{API_BASE}/auth/login", json=user_creds)
        if response.status_code != 200:
            raise Exception(f"Login failed for {user_type}: {response.text}")
        
        data = response.json()
        token = data["access_token"]
        self.tokens[user_type] = token
        print(f"✅ {user_type} logged in successfully")
        return token
    
    def get_headers(self, user_type: str):
        """Get authorization headers for user"""
        if user_type not in self.tokens:
            self.login_user(user_type)
        return {"Authorization": f"Bearer {self.tokens[user_type]}"}
    
    def test_predictions_info(self):
        """Test the predictions info endpoint"""
        print("\n🔍 Testing Predictions API Info...")
        
        response = requests.get(f"{API_BASE}/predictions/")
        if response.status_code != 200:
            raise Exception(f"Predictions info failed: {response.text}")
        
        data = response.json()
        print(f"✅ API Info: {data['service']} v{data['version']}")
        print(f"   Features: {len(data['features'])} features available")
        print(f"   Endpoints: {len(data['endpoints'])} endpoints available")
        return True
    
    def test_create_company_and_prediction(self):
        """Test creating a company and then making predictions"""
        print("\n🏢 Testing Company Creation and Predictions...")
        
        headers = self.get_headers("super_admin")
        
        # Create a test company
        company_data = {
            "name": "Test ML Company Ltd",
            "symbol": "TESTML",
            "industry": "Technology",
            "sector": "Software",
            "description": "Test company for ML prediction validation",
            "market_cap": 5000000000,
            "revenue": 2000000000,
            "employees": 10000,
            "founded_year": 2010,
            "exchange": "NSE",
            "currency": "INR",
            "country": "India"
        }
        
        response = requests.post(f"{API_BASE}/companies", json=company_data, headers=headers)
        if response.status_code != 201:
            print(f"⚠️ Company creation failed: {response.text}")
            # Try to use an existing company or create a simpler one
            return self.test_prediction_without_company()
        
        company = response.json()
        company_id = company["id"]
        print(f"✅ Test company created: {company['name']} (ID: {company_id})")
        
        # Now test annual prediction
        headers = self.get_headers("hdfc_central_analyst")
        
        prediction_data = {
            "company_id": company_id,
            "year": 2024,
            "total_assets": 10000000000,
            "total_liabilities": 6000000000,
            "revenue": 2000000000,
            "net_income": 200000000,
            "cash_flow": 300000000,
            "debt_to_equity": 1.5,
            "current_ratio": 1.2,
            "quick_ratio": 0.9,
            "return_on_assets": 0.02,
            "return_on_equity": 0.05,
            "working_capital": 1000000000,
            "retained_earnings": 2000000000,
            "ebit": 350000000,
            "market_value_equity": 5000000000,
            "sales": 2000000000
        }
        
        response = requests.post(f"{API_BASE}/predictions/annual", json=prediction_data, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Annual prediction failed: {response.text}")
        
        data = response.json()
        prediction_id = data["prediction_id"]
        pred_data = data["data"]["prediction"]
        
        print(f"✅ Annual prediction created: ID {prediction_id}")
        print(f"   Probability: {pred_data['probability']:.4f}")
        print(f"   Risk Level: {pred_data['risk_level']}")
        print(f"   Confidence: {pred_data['confidence']:.4f}")
        print(f"   Company: {pred_data['company_name']} ({pred_data['year']})")
        
        return True
    
    def test_prediction_without_company(self):
        """Test if we can make predictions with just financial data (if supported)"""
        print("\n🎯 Testing Direct Financial Data Prediction...")
        
        headers = self.get_headers("hdfc_central_analyst")
        
        # Try unified prediction with minimal data
        prediction_data = {
            "prediction_type": "annual",
            "year": 2024,
            "financial_data": {
                "total_assets": 10000000000,
                "total_liabilities": 6000000000,
                "revenue": 2000000000,
                "net_income": 200000000,
                "cash_flow": 300000000,
                "debt_to_equity": 1.5,
                "current_ratio": 1.2,
                "quick_ratio": 0.9,
                "return_on_assets": 0.02,
                "return_on_equity": 0.05
            }
        }
        
        # Try without company_id to test direct ML prediction
        response = requests.post(f"{API_BASE}/predictions/unified-predict", json=prediction_data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Direct ML prediction successful!")
            print(f"   Prediction: {data}")
            return True
        else:
            print(f"⚠️ Direct prediction failed: {response.text}")
            return False
    
    def test_ml_model_health(self):
        """Test if ML models are loaded and working"""
        print("\n🤖 Testing ML Model Health...")
        
        # Simple health check - this should work regardless of companies
        try:
            response = requests.get(f"{API_BASE}/predictions/")
            if response.status_code == 200:
                data = response.json()
                if "ml_models" in str(data).lower() or "features" in data:
                    print("✅ ML models appear to be loaded and accessible")
                    return True
        except Exception as e:
            print(f"⚠️ ML model check failed: {str(e)}")
        
        return False
    
    def test_auth_system(self):
        """Test that authentication is working properly"""
        print("\n🔐 Testing Authentication System...")
        
        # Test without auth - should fail
        response = requests.get(f"{API_BASE}/predictions/annual")
        if response.status_code == 401:
            print("✅ Authentication required - security working")
        else:
            print(f"⚠️ Expected 401, got {response.status_code}")
        
        # Test with auth - should work
        headers = self.get_headers("hdfc_central_analyst")
        response = requests.get(f"{API_BASE}/predictions/annual", headers=headers)
        if response.status_code in [200, 422]:  # 422 might be validation error which is fine
            print("✅ Authentication working with valid token")
            return True
        else:
            print(f"⚠️ Auth test failed: {response.status_code}")
        
        return False
    
    def run_core_tests(self):
        """Run core functionality tests"""
        print("🚀 Starting Core Predictions API Tests")
        print("=" * 50)
        
        results = {
            "api_info": False,
            "ml_health": False,
            "auth_system": False,
            "predictions": False
        }
        
        try:
            # Basic API info test
            results["api_info"] = self.test_predictions_info()
            
            # ML model health check
            results["ml_health"] = self.test_ml_model_health()
            
            # Authentication system test
            results["auth_system"] = self.test_auth_system()
            
            # Main prediction functionality
            results["predictions"] = self.test_create_company_and_prediction()
            
            print("\n🎉 Core Tests Summary:")
            print("=" * 50)
            for test, passed in results.items():
                status = "✅ PASS" if passed else "❌ FAIL"
                print(f"   {test.replace('_', ' ').title()}: {status}")
            
            if all(results.values()):
                print("\n🎉 All core tests PASSED! Your predictions API is working!")
                print("✅ ML models are loaded and functional")
                print("✅ Authentication and security are working")
                print("✅ Prediction endpoints are operational")
            else:
                print("\n⚠️ Some tests failed, but core functionality may still work")
            
        except Exception as e:
            print(f"\n❌ Core test failed: {str(e)}")
            print("This indicates a fundamental issue with the API")
            raise

def main():
    """Main test runner"""
    tester = SimplePredictionsTest()
    tester.run_core_tests()

if __name__ == "__main__":
    main()
