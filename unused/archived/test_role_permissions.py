#!/usr/bin/env python3
"""
Test role-based permissions for company and prediction creation
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_login(email, password):
    """Test login and return token"""
    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Login successful for {email}")
        
        # Handle different response formats
        if 'user' in data:
            user_data = data['user']
            print(f"   Role: {user_data.get('role', 'Unknown')}")
            print(f"   Organization: {user_data.get('organization_id', 'None')}")
            return data.get("access_token")
        else:
            # If no user key, just return token
            print(f"   Response keys: {list(data.keys())}")
            return data.get("access_token") or data.get("token")
    else:
        print(f"❌ Login failed for {email}: {response.text}")
        return None

def test_company_creation(token, role_name):
    """Test company creation with given token"""
    print(f"\n🏭 Testing company creation as {role_name}...")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    company_data = {
        "symbol": f"TEST{role_name.upper()}",
        "name": f"Test Company {role_name}",
        "market_cap": 1000000000,
        "sector": "Technology"
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/companies/", 
                           json=company_data, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Company creation successful for {role_name}")
        return response.json()
    else:
        print(f"❌ Company creation failed for {role_name}: {response.text}")
        return None

def test_prediction_creation(token, role_name, company_name="Apple Inc."):
    """Test prediction creation with given token"""
    print(f"\n📊 Testing prediction creation as {role_name}...")
    
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    prediction_data = {
        "company_name": company_name,
        "revenue": 365000000000,  # $365B
        "expenses": 280000000000,  # $280B  
        "assets": 350000000000,   # $350B
        "liabilities": 290000000000,  # $290B
        "year": 2024
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/predictions/annual", 
                           json=prediction_data, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Prediction creation successful for {role_name}")
        return response.json()
    else:
        print(f"❌ Prediction creation failed for {role_name}: {response.text}")
        return None

def test_role_permissions():
    """Test permissions for different roles"""
    print("🔒 Testing Role-Based Permissions...")
    print("="*60)
    
    # Test users from our banking data
    test_users = [
        {
            "email": "pranitsuperadmin@gmail.com",
            "password": "SuperAdmin123!",
            "role": "super_admin",
            "should_create_company": True,
            "should_create_prediction": True
        },
        {
            "email": "admin@hdfcbank.com", 
            "password": "HdfcBankAdmin123!",
            "role": "tenant_admin",
            "should_create_company": True,
            "should_create_prediction": True
        },
        {
            "email": "manager.central@hdfcbank.com",
            "password": "HdfcCentralManager123!",
            "role": "org_admin",
            "should_create_company": True,
            "should_create_prediction": True
        },
        {
            "email": "rohan.analyst@hdfcbank.com",
            "password": "RohanHdfc123!",
            "role": "org_member",
            "should_create_company": True,  # THIS IS WHAT WE WANT TO TEST
            "should_create_prediction": True  # THIS IS WHAT WE WANT TO TEST
        },
        {
            "email": "consultant@defaultrate.com",
            "password": "Consultant123!",
            "role": "user",
            "should_create_company": False,
            "should_create_prediction": False
        }
    ]
    
    results = {}
    
    for user in test_users:
        print(f"\n👤 Testing {user['role']}: {user['email']}")
        print("-" * 50)
        
        # Test login
        token = test_login(user['email'], user['password'])
        if not token:
            continue
        
        results[user['role']] = {'login': True}
        
        # Test company creation
        company_result = test_company_creation(token, user['role'])
        results[user['role']]['company_creation'] = company_result is not None
        
        # Test prediction creation (use existing global company)
        prediction_result = test_prediction_creation(token, user['role'], "Apple Inc.")
        results[user['role']]['prediction_creation'] = prediction_result is not None
        
        # Check if results match expectations
        company_matches = results[user['role']]['company_creation'] == user['should_create_company']
        prediction_matches = results[user['role']]['prediction_creation'] == user['should_create_prediction']
        
        if company_matches and prediction_matches:
            print(f"✅ {user['role']} permissions working correctly")
        else:
            print(f"❌ {user['role']} permissions not working as expected:")
            print(f"   Company creation: expected {user['should_create_company']}, got {results[user['role']]['company_creation']}")
            print(f"   Prediction creation: expected {user['should_create_prediction']}, got {results[user['role']]['prediction_creation']}")
    
    # Summary
    print(f"\n📋 PERMISSION TEST SUMMARY")
    print("="*60)
    for role, result in results.items():
        print(f"{role:15} | Login: {result.get('login', False):5} | Company: {result.get('company_creation', False):5} | Prediction: {result.get('prediction_creation', False):5}")
    
    return results

def test_organization_context():
    """Test that predictions are saved in correct organization context"""
    print(f"\n🏛️ Testing Organization Context...")
    print("="*60)
    
    # Login as org member from HDFC Central
    token = test_login("rohan.analyst@hdfcbank.com", "RohanHdfc123!")
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get organizations to see current context
    org_response = requests.get(f"{BASE_URL}/api/v1/organizations/", headers=headers)
    if org_response.status_code == 200:
        orgs = org_response.json()
        print(f"✅ User can see {orgs.get('total', 0)} organizations")
        if orgs.get('organizations'):
            for org in orgs['organizations']:
                print(f"   - {org['name']} (ID: {org['id']})")
    
    # Test creating company and check if it's linked to correct organization
    company_result = test_company_creation(token, "org_member_context_test")
    
    # Test creating prediction and check organization linkage
    prediction_result = test_prediction_creation(token, "org_member_context_test", "Apple Inc.")

if __name__ == "__main__":
    print("🚀 Starting Role Permission Tests...")
    
    try:
        # Test basic role permissions
        results = test_role_permissions()
        
        # Test organization context
        test_organization_context()
        
        print(f"\n🎯 Testing completed!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
