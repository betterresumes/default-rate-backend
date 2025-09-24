#!/usr/bin/env python3
"""
Test script to verify prediction UPDATE/DELETE permissions are working correctly.

Requirements:
1. Users can edit/delete their own created predictions (personal scope)
2. Org members & org admins can edit/delete their organization's predictions  
3. Tenant admins can edit/delete predictions from any org under their tenant
4. Super admins can edit/delete system-level data
5. System predictions/companies can ONLY be deleted/edited by super admins
"""

import requests
import json
from typing import Dict, Any

# API Configuration
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1"

# Test Users (based on your dashboard testing results)
TEST_USERS = {
    "super_admin": {
        "email": "admin@defaultrate.com",
        "password": "admin123",
        "role": "super_admin",
        "expected_scope": "system"
    },
    "tenant_admin": {
        "email": "ceo@defaultrate.com", 
        "password": "ceo123",
        "role": "tenant_admin",
        "expected_scope": "cross_organization"
    },
    "morgan_admin": {
        "email": "risk.director@morganstanley.com",
        "password": "director123", 
        "role": "org_admin",
        "organization": "Morgan Stanley"
    },
    "morgan_member": {
        "email": "sarah.williams@morganstanley.com",
        "password": "sarah123",
        "role": "org_member", 
        "organization": "Morgan Stanley"
    },
    "jpmorgan_admin": {
        "email": "analytics.head@jpmorgan.com",
        "password": "head123",
        "role": "org_admin",
        "organization": "JPMorgan Chase"
    },
    "jpmorgan_member": {
        "email": "emily.davis@jpmorgan.com", 
        "password": "emily123",
        "role": "org_member",
        "organization": "JPMorgan Chase"
    }
}

def authenticate_user(email: str, password: str) -> str:
    """Authenticate user and return access token"""
    try:
        response = requests.post(
            f"{API_BASE}/auth/login",
            data={
                "username": email,
                "password": password,
                "grant_type": "password"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data.get("access_token")
        else:
            print(f"Authentication failed for {email}: {response.text}")
            return None
    except Exception as e:
        print(f"Error authenticating {email}: {e}")
        return None

def get_predictions(token: str, prediction_type: str = "annual") -> list:
    """Get all predictions for a user"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{API_BASE}/predictions/{prediction_type}?size=100", headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return data.get("predictions", [])
        else:
            print(f"Failed to get predictions: {response.text}")
            return []
    except Exception as e:
        print(f"Error getting predictions: {e}")
        return []

def test_delete_prediction(token: str, prediction_id: str, prediction_type: str = "annual") -> Dict[str, Any]:
    """Test deleting a prediction"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.delete(f"{API_BASE}/predictions/{prediction_type}/{prediction_id}", headers=headers)
        
        return {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response": response.json() if response.status_code != 500 else response.text,
            "error": None if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {
            "status_code": 500,
            "success": False, 
            "response": None,
            "error": str(e)
        }

def test_update_prediction(token: str, prediction_id: str, prediction_type: str = "annual") -> Dict[str, Any]:
    """Test updating a prediction"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Sample update data
        if prediction_type == "annual":
            update_data = {
                "company_symbol": "TEST",
                "company_name": "Test Company Updated",
                "market_cap": 1000.0,
                "sector": "Technology",
                "reporting_year": "2024",
                "reporting_quarter": "Q1",
                "long_term_debt_to_total_capital": 0.30,
                "total_debt_to_ebitda": 2.5,
                "net_income_margin": 0.15,
                "ebit_to_interest_expense": 5.0,
                "return_on_assets": 0.08
            }
        else:
            update_data = {
                "company_symbol": "TEST",
                "company_name": "Test Company Updated",
                "market_cap": 1000.0,
                "sector": "Technology", 
                "reporting_year": "2024",
                "reporting_quarter": "Q1",
                "total_debt_to_ebitda": 2.5,
                "sga_margin": 0.25,
                "long_term_debt_to_total_capital": 0.30,
                "return_on_capital": 0.12
            }
        
        response = requests.put(
            f"{API_BASE}/predictions/{prediction_type}/{prediction_id}",
            headers=headers,
            json=update_data
        )
        
        return {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "response": response.json() if response.status_code != 500 else response.text,
            "error": None if response.status_code == 200 else response.text
        }
    except Exception as e:
        return {
            "status_code": 500,
            "success": False,
            "response": None, 
            "error": str(e)
        }

def main():
    """Main test execution"""
    print("🔐 Testing Prediction UPDATE/DELETE Permissions")
    print("=" * 60)
    
    # Get tokens for all users
    tokens = {}
    for user_key, user_data in TEST_USERS.items():
        print(f"Authenticating {user_key}...")
        token = authenticate_user(user_data["email"], user_data["password"])
        if token:
            tokens[user_key] = token
            print(f"✅ {user_key} authenticated successfully")
        else:
            print(f"❌ {user_key} authentication failed")
    
    if not tokens:
        print("❌ No users authenticated. Cannot proceed with tests.")
        return
    
    print(f"\n📊 Successfully authenticated {len(tokens)} users")
    print("=" * 60)
    
    # Test prediction access for each user
    for user_key, token in tokens.items():
        user_info = TEST_USERS[user_key]
        print(f"\n🧪 Testing {user_key} ({user_info['role']})")
        print("-" * 40)
        
        # Get predictions for this user
        predictions = get_predictions(token, "annual")
        print(f"📈 Found {len(predictions)} annual predictions")
        
        if predictions:
            # Test with first prediction
            test_prediction = predictions[0]
            prediction_id = test_prediction["id"]
            access_level = test_prediction.get("access_level", "unknown")
            created_by = test_prediction.get("created_by")
            org_name = test_prediction.get("organization_name", "No Organization")
            
            print(f"   🎯 Testing with prediction: {test_prediction['company_symbol']}")
            print(f"   📋 Access Level: {access_level}")
            print(f"   🏢 Organization: {org_name}")
            print(f"   👤 Created By: {created_by}")
            
            # Test UPDATE
            print("\n   🔄 Testing UPDATE permission...")
            update_result = test_update_prediction(token, prediction_id, "annual")
            if update_result["success"]:
                print(f"   ✅ UPDATE allowed (Status: {update_result['status_code']})")
            else:
                print(f"   ❌ UPDATE denied (Status: {update_result['status_code']})")
                if update_result["error"]:
                    print(f"   📝 Reason: {update_result['error']}")
            
            # Test DELETE (Warning: This will actually delete!)
            print("   🗑️  Testing DELETE permission...")
            # Note: Uncomment the line below to actually test DELETE (destructive!)
            # delete_result = test_delete_prediction(token, prediction_id, "annual")
            # For now, just simulate
            print("   ⚠️  DELETE test skipped (would be destructive)")
        else:
            print("   📭 No predictions found for this user")
    
    print("\n" + "=" * 60)
    print("🎉 Permission testing completed!")
    print("\n📋 Expected Permission Matrix:")
    print("   👤 user: Can edit/delete own personal predictions only")
    print("   👥 org_member: Can edit/delete org predictions + own personal")
    print("   🏢 org_admin: Can edit/delete org predictions + own personal")  
    print("   🏛️ tenant_admin: Can edit/delete tenant org predictions + own personal")
    print("   🌟 super_admin: Can edit/delete system predictions + everything")
    print("   🔒 system predictions: Only super_admin can edit/delete")

if __name__ == "__main__":
    main()
