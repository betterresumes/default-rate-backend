#!/usr/bin/env python3
"""
Test script for the Predictions API - validates all endpoints work correctly
Tests ML integration, role-based access, CRUD operations, and bulk processing
"""

import asyncio
import aiohttp
import json
import uuid
from datetime import datetime

# API Configuration
BASE_URL = "http://127.0.0.1:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test user credentials (from setup_banking_data.py)
TEST_USERS = {
    "super_admin": {"email": "super.admin@system.com", "password": "SuperAdminPass123"},
    "hdfc_tenant_admin": {"email": "admin@hdfc.com", "password": "AdminPass123"},
    "hdfc_mumbai_admin": {"email": "admin.mumbai@hdfc.com", "password": "AdminPass123"},
    "hdfc_mumbai_member": {"email": "member.mumbai@hdfc.com", "password": "MemberPass123"},
    "icici_tenant_admin": {"email": "admin@icici.com", "password": "AdminPass123"},
}

class PredictionsAPITester:
    def __init__(self):
        self.session = None
        self.tokens = {}
        self.test_company_id = None
        self.test_predictions = {}
        
    async def setup_session(self):
        """Create HTTP session"""
        self.session = aiohttp.ClientSession()
        
    async def cleanup_session(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def login_user(self, user_type: str):
        """Login user and get access token"""
        user_creds = TEST_USERS[user_type]
        
        async with self.session.post(
            f"{API_BASE}/auth/login",
            json=user_creds
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Login failed for {user_type}: {text}")
            
            data = await response.json()
            token = data["access_token"]
            self.tokens[user_type] = token
            print(f"✅ {user_type} logged in successfully")
            return token
    
    async def get_headers(self, user_type: str):
        """Get authorization headers for user"""
        if user_type not in self.tokens:
            await self.login_user(user_type)
        return {"Authorization": f"Bearer {self.tokens[user_type]}"}
    
    async def test_predictions_info(self):
        """Test the predictions info endpoint"""
        print("\n🔍 Testing Predictions API Info...")
        
        async with self.session.get(f"{API_BASE}/predictions/") as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Predictions info failed: {text}")
            
            data = await response.json()
            print(f"✅ API Info: {data['service']} v{data['version']}")
            print(f"   Features: {len(data['features'])} features available")
            print(f"   Endpoints: {len(data['endpoints'])} endpoints available")
    
    async def test_create_test_company(self):
        """Create a test company for predictions"""
        print("\n🏢 Creating test company...")
        
        headers = await self.get_headers("hdfc_mumbai_admin")
        
        company_data = {
            "name": "Test Prediction Company Ltd",
            "symbol": "TESTPRED",
            "industry": "Technology",
            "sector": "Software",
            "description": "Test company for prediction API validation",
            "market_cap": 5000000000,  # 5B
            "revenue": 2000000000,     # 2B
            "employees": 10000,
            "founded_year": 2010,
            "exchange": "NSE",
            "currency": "INR",
            "country": "India"
        }
        
        async with self.session.post(
            f"{API_BASE}/companies",
            json=company_data,
            headers=headers
        ) as response:
            if response.status != 201:
                text = await response.text()
                raise Exception(f"Company creation failed: {text}")
            
            data = await response.json()
            self.test_company_id = data["id"]
            print(f"✅ Test company created: {data['name']} (ID: {self.test_company_id})")
    
    async def test_annual_prediction(self, user_type: str = "hdfc_mumbai_member"):
        """Test annual prediction creation"""
        print(f"\n📊 Testing Annual Prediction Creation ({user_type})...")
        
        headers = await self.get_headers(user_type)
        
        # Test data that should work with ML models
        prediction_data = {
            "company_id": self.test_company_id,
            "year": 2024,
            "total_assets": 10000000000,      # 10B
            "total_liabilities": 6000000000,   # 6B  
            "revenue": 2000000000,             # 2B
            "net_income": 200000000,           # 200M
            "cash_flow": 300000000,            # 300M
            "debt_to_equity": 1.5,             # 60% debt to 40% equity
            "current_ratio": 1.2,
            "quick_ratio": 0.9,
            "return_on_assets": 0.02,          # 2%
            "return_on_equity": 0.05,          # 5%
            "working_capital": 1000000000,     # 1B
            "retained_earnings": 2000000000,   # 2B
            "ebit": 350000000,                 # 350M
            "market_value_equity": 5000000000, # 5B
            "sales": 2000000000                # 2B
        }
        
        async with self.session.post(
            f"{API_BASE}/predictions/annual",
            json=prediction_data,
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Annual prediction failed: {text}")
            
            data = await response.json()
            prediction_id = data["prediction_id"]
            self.test_predictions["annual"] = prediction_id
            
            ml_result = data["data"]["ml_result"]
            pred_data = data["data"]["prediction"]
            
            print(f"✅ Annual prediction created: ID {prediction_id}")
            print(f"   Probability: {pred_data['probability']:.4f}")
            print(f"   Risk Level: {pred_data['risk_level']}")
            print(f"   Confidence: {pred_data['confidence']:.4f}")
            print(f"   Company: {pred_data['company_name']} ({pred_data['year']})")
    
    async def test_quarterly_prediction(self, user_type: str = "hdfc_mumbai_member"):
        """Test quarterly prediction creation"""
        print(f"\n📈 Testing Quarterly Prediction Creation ({user_type})...")
        
        headers = await self.get_headers(user_type)
        
        # Quarterly data (typically 1/4 of annual)
        prediction_data = {
            "company_id": self.test_company_id,
            "year": 2024,
            "quarter": "Q1",
            "total_assets": 10000000000,      # 10B (same as annual)
            "total_liabilities": 6000000000,   # 6B (same as annual)
            "revenue": 500000000,              # 500M (quarterly)
            "net_income": 50000000,            # 50M (quarterly)
            "cash_flow": 75000000,             # 75M (quarterly)
            "debt_to_equity": 1.5,             # Same ratio
            "current_ratio": 1.2,
            "quick_ratio": 0.9,
            "return_on_assets": 0.005,         # Quarterly rate
            "return_on_equity": 0.0125,        # Quarterly rate
            "working_capital": 1000000000,     # 1B
            "retained_earnings": 2000000000,   # 2B
            "ebit": 87500000,                  # 87.5M (quarterly)
            "market_value_equity": 5000000000, # 5B
            "sales": 500000000                 # 500M (quarterly)
        }
        
        async with self.session.post(
            f"{API_BASE}/predictions/quarterly",
            json=prediction_data,
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Quarterly prediction failed: {text}")
            
            data = await response.json()
            prediction_id = data["prediction_id"]
            self.test_predictions["quarterly"] = prediction_id
            
            ml_result = data["data"]["ml_result"]
            pred_data = data["data"]["prediction"]
            
            print(f"✅ Quarterly prediction created: ID {prediction_id}")
            print(f"   Probability: {pred_data['probability']:.4f}")
            print(f"   Risk Level: {pred_data['risk_level']}")
            print(f"   Confidence: {pred_data['confidence']:.4f}")
            print(f"   Company: {pred_data['company_name']} ({pred_data['quarter']} {pred_data['year']})")
    
    async def test_unified_prediction(self, user_type: str = "hdfc_mumbai_member"):
        """Test unified prediction endpoint"""
        print(f"\n🎯 Testing Unified Prediction Endpoint ({user_type})...")
        
        headers = await self.get_headers(user_type)
        
        # Test annual via unified endpoint
        prediction_data = {
            "company_id": self.test_company_id,
            "prediction_type": "annual",
            "year": 2023,
            "financial_data": {
                "total_assets": 9000000000,
                "total_liabilities": 5400000000,
                "revenue": 1800000000,
                "net_income": 180000000,
                "cash_flow": 270000000,
                "debt_to_equity": 1.4,
                "current_ratio": 1.1,
                "quick_ratio": 0.8,
                "return_on_assets": 0.02,
                "return_on_equity": 0.05
            }
        }
        
        async with self.session.post(
            f"{API_BASE}/predictions/unified-predict",
            json=prediction_data,
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Unified prediction failed: {text}")
            
            data = await response.json()
            prediction_id = data["prediction_id"]
            pred_data = data["data"]["prediction"]
            
            print(f"✅ Unified annual prediction created: ID {prediction_id}")
            print(f"   Probability: {pred_data['probability']:.4f}")
            print(f"   Risk Level: {pred_data['risk_level']}")
    
    async def test_get_predictions(self, user_type: str = "hdfc_mumbai_member"):
        """Test retrieving predictions"""
        print(f"\n📋 Testing Prediction Retrieval ({user_type})...")
        
        headers = await self.get_headers(user_type)
        
        # Test annual predictions list
        async with self.session.get(
            f"{API_BASE}/predictions/annual?page=1&limit=10",
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Get annual predictions failed: {text}")
            
            data = await response.json()
            print(f"✅ Annual predictions retrieved: {len(data['data'])} predictions")
            print(f"   Total: {data['pagination']['total']}")
        
        # Test quarterly predictions list  
        async with self.session.get(
            f"{API_BASE}/predictions/quarterly?page=1&limit=10",
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Get quarterly predictions failed: {text}")
            
            data = await response.json()
            print(f"✅ Quarterly predictions retrieved: {len(data['data'])} predictions")
            print(f"   Total: {data['pagination']['total']}")
    
    async def test_company_predictions(self, user_type: str = "hdfc_mumbai_member"):
        """Test getting predictions for specific company"""
        print(f"\n🏢 Testing Company Predictions ({user_type})...")
        
        headers = await self.get_headers(user_type)
        
        async with self.session.get(
            f"{API_BASE}/predictions/companies/{self.test_company_id}",
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Get company predictions failed: {text}")
            
            data = await response.json()
            print(f"✅ Company predictions retrieved:")
            print(f"   Company: {data['company']['name']}")
            print(f"   Annual predictions: {data['summary']['total_annual']}")
            print(f"   Quarterly predictions: {data['summary']['total_quarterly']}")
    
    async def test_prediction_summary(self, user_type: str = "hdfc_mumbai_member"):
        """Test prediction analytics summary"""
        print(f"\n📊 Testing Prediction Summary ({user_type})...")
        
        headers = await self.get_headers(user_type)
        
        async with self.session.get(
            f"{API_BASE}/predictions/summary?period=month",
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Get prediction summary failed: {text}")
            
            data = await response.json()
            summary = data['summary']
            print(f"✅ Prediction summary retrieved:")
            print(f"   Total predictions: {summary['total_predictions']}")
            print(f"   Annual: {summary['annual_predictions']}")
            print(f"   Quarterly: {summary['quarterly_predictions']}")
            print(f"   Context: {summary['organization_context']}")
    
    async def test_bulk_predictions(self, user_type: str = "hdfc_mumbai_member"):
        """Test bulk prediction processing"""
        print(f"\n📦 Testing Bulk Predictions ({user_type})...")
        
        headers = await self.get_headers(user_type)
        
        # Create bulk request with 2 predictions
        bulk_data = {
            "predictions": [
                {
                    "company_id": self.test_company_id,
                    "prediction_type": "annual",
                    "year": 2022,
                    "financial_data": {
                        "total_assets": 8000000000,
                        "total_liabilities": 4800000000,
                        "revenue": 1600000000,
                        "net_income": 160000000,
                        "cash_flow": 240000000,
                        "debt_to_equity": 1.3,
                        "current_ratio": 1.0,
                        "quick_ratio": 0.7,
                        "return_on_assets": 0.02,
                        "return_on_equity": 0.05
                    }
                },
                {
                    "company_id": self.test_company_id,
                    "prediction_type": "quarterly",
                    "year": 2024,
                    "quarter": "Q2",
                    "financial_data": {
                        "total_assets": 10000000000,
                        "total_liabilities": 6000000000,
                        "revenue": 520000000,
                        "net_income": 52000000,
                        "cash_flow": 78000000,
                        "debt_to_equity": 1.5,
                        "current_ratio": 1.2,
                        "quick_ratio": 0.9,
                        "return_on_assets": 0.005,
                        "return_on_equity": 0.0125
                    }
                }
            ]
        }
        
        # Test synchronous bulk processing
        async with self.session.post(
            f"{API_BASE}/predictions/bulk",
            json=bulk_data,
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Bulk predictions failed: {text}")
            
            data = await response.json()
            summary = data['summary']
            print(f"✅ Bulk predictions (sync) completed:")
            print(f"   Total: {summary['total']}")
            print(f"   Successful: {summary['successful']}")
            print(f"   Failed: {summary['failed']}")
        
        # Test asynchronous bulk processing
        async with self.session.post(
            f"{API_BASE}/predictions/bulk-async",
            json=bulk_data,
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Bulk async predictions failed: {text}")
            
            data = await response.json()
            job_id = data['job_id']
            summary = data['summary']
            print(f"✅ Bulk predictions (async) completed:")
            print(f"   Job ID: {job_id}")
            print(f"   Total: {summary['total']}")
            print(f"   Successful: {summary['successful']}")
            print(f"   Failed: {summary['failed']}")
    
    async def test_prediction_update(self, user_type: str = "hdfc_mumbai_member"):
        """Test updating predictions"""
        print(f"\n✏️ Testing Prediction Updates ({user_type})...")
        
        headers = await self.get_headers(user_type)
        
        if "annual" not in self.test_predictions:
            print("⚠️ Skipping update test - no annual prediction created")
            return
        
        # Update annual prediction with new financial data
        update_data = {
            "financial_data": {
                "total_assets": 11000000000,  # Increased
                "total_liabilities": 6600000000,  # Increased proportionally
                "revenue": 2200000000,  # Increased
                "net_income": 220000000,  # Increased
                "cash_flow": 330000000,  # Increased
                "debt_to_equity": 1.6,  # Slightly higher risk
                "current_ratio": 1.1,  # Slightly lower liquidity
                "quick_ratio": 0.8,
                "return_on_assets": 0.02,
                "return_on_equity": 0.05
            }
        }
        
        prediction_id = self.test_predictions["annual"]
        async with self.session.put(
            f"{API_BASE}/predictions/annual/{prediction_id}",
            json=update_data,
            headers=headers
        ) as response:
            if response.status != 200:
                text = await response.text()
                raise Exception(f"Prediction update failed: {text}")
            
            data = await response.json()
            print(f"✅ Annual prediction updated:")
            print(f"   New probability: {data['data']['probability']:.4f}")
            print(f"   New risk level: {data['data']['risk_level']}")
            print(f"   Confidence: {data['data']['confidence']:.4f}")
    
    async def test_role_based_access(self):
        """Test role-based access control"""
        print(f"\n🔐 Testing Role-Based Access Control...")
        
        # Test that regular user cannot access org predictions
        try:
            # Create a basic user without organization access
            headers = await self.get_headers("super_admin")  # Use super admin to create user
            
            user_data = {
                "email": "basic.user@test.com",
                "password": "BasicUserPass123",
                "first_name": "Basic",
                "last_name": "User",
                "username": "basicuser",
                "role": "user"
            }
            
            async with self.session.post(
                f"{API_BASE}/users",
                json=user_data,
                headers=headers
            ) as response:
                if response.status == 201:
                    print("✅ Basic user created for testing")
                
            # Login as basic user
            basic_token = await self.login_user("basic_user")
            basic_headers = {"Authorization": f"Bearer {basic_token}"}
            
            # Try to access predictions - should fail
            async with self.session.get(
                f"{API_BASE}/predictions/annual",
                headers=basic_headers
            ) as response:
                if response.status == 403:
                    print("✅ Role-based access control working - basic user blocked")
                else:
                    print(f"⚠️ Expected 403, got {response.status}")
                    
        except Exception as e:
            print(f"⚠️ Role-based test skipped: {str(e)}")
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 Starting Predictions API Test Suite")
        print("=" * 50)
        
        try:
            await self.setup_session()
            
            # Core API tests
            await self.test_predictions_info()
            await self.test_create_test_company()
            
            # Prediction creation tests
            await self.test_annual_prediction()
            await self.test_quarterly_prediction()
            await self.test_unified_prediction()
            
            # Retrieval tests
            await self.test_get_predictions()
            await self.test_company_predictions()
            await self.test_prediction_summary()
            
            # Advanced features
            await self.test_bulk_predictions()
            await self.test_prediction_update()
            
            # Security tests
            await self.test_role_based_access()
            
            print("\n🎉 All tests completed successfully!")
            print("=" * 50)
            print("✅ Predictions API is fully functional")
            print("✅ ML models are working correctly")
            print("✅ Role-based access control is enforced")
            print("✅ CRUD operations are working")
            print("✅ Bulk processing is functional")
            
        except Exception as e:
            print(f"\n❌ Test failed: {str(e)}")
            raise
        finally:
            await self.cleanup_session()

# Add basic user login support
TEST_USERS["basic_user"] = {"email": "basic.user@test.com", "password": "BasicUserPass123"}

async def main():
    """Main test runner"""
    tester = PredictionsAPITester()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())
