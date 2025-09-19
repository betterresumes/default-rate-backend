#!/usr/bin/env python3
"""
Test the role system and permissions for companies and predictions
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_authentication():
    """Test login and get tokens for different users"""
    users = {
        "super_admin": {
            "email": "superadmin@defaultrate.com",
            "password": "superadmin123"
        },
        "tenant_admin": {
            "email": "admin.hdfc@hdfcbank.com", 
            "password": "hdfc_admin_2024"
        },
        "org_admin": {
            "email": "manager.central@hdfcbank.com",
            "password": "manager_central_2024"
        },
        "org_member": {
            "email": "analyst.central@hdfcbank.com",
            "password": "analyst_central_2024"
        }
    }
    
    tokens = {}
    
    for role, credentials in users.items():
        print(f"\n🔐 Testing login for {role}...")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/login",
            json=credentials,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            tokens[role] = data["access_token"]
            user_info = data["user"]
            print(f"   ✅ Login successful")
            print(f"   📧 Email: {user_info['email']}")
            print(f"   👤 Role: {user_info['role']}")
            print(f"   🏢 Tenant ID: {user_info.get('tenant_id', 'None')}")
            print(f"   🏛️  Organization ID: {user_info.get('organization_id', 'None')}")
        else:
            print(f"   ❌ Login failed: {response.status_code}")
            print(f"   📝 Response: {response.text}")
    
    return tokens

def test_company_creation(tokens):
    """Test company creation with different roles"""
    print(f"\n{'='*60}")
    print("🏭 TESTING COMPANY CREATION")
    print(f"{'='*60}")
    
    test_company = {
        "symbol": "TESTCO",
        "name": "Test Company Ltd",
        "market_cap": 1000000000,
        "sector": "Technology"
    }
    
    for role, token in tokens.items():
        print(f"\n📝 Testing company creation as {role}...")
        
        # Modify symbol to avoid conflicts
        test_company["symbol"] = f"TEST{role.upper()[:3]}"
        test_company["name"] = f"Test Company {role.title()}"
        
        response = requests.post(
            f"{BASE_URL}/api/v1/companies/",
            json=test_company,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            print(f"   ✅ Company creation successful")
            data = response.json()
            print(f"   📊 Company: {data.get('company', {}).get('name', 'Unknown')}")
        else:
            print(f"   ❌ Company creation failed: {response.status_code}")
            print(f"   📝 Response: {response.text}")

def test_organization_access(tokens):
    """Test organization API access with different roles"""
    print(f"\n{'='*60}")
    print("🏛️  TESTING ORGANIZATION ACCESS")
    print(f"{'='*60}")
    
    for role, token in tokens.items():
        print(f"\n🔍 Testing organization access as {role}...")
        
        response = requests.get(
            f"{BASE_URL}/api/v1/organizations/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            orgs = data.get("organizations", [])
            print(f"   ✅ Access successful - Can see {len(orgs)} organizations")
            
            for org in orgs[:2]:  # Show first 2 organizations
                print(f"   📋 {org['name']} (Tenant: {org.get('tenant', {}).get('name', 'Unknown')})")
                if org.get('tenant', {}).get('tenant_admins'):
                    admin_count = len(org['tenant']['tenant_admins'])
                    print(f"       👥 Tenant Admins: {admin_count}")
        else:
            print(f"   ❌ Access failed: {response.status_code}")
            print(f"   📝 Response: {response.text}")

def test_predictions_access(tokens):
    """Test if users can access predictions"""
    print(f"\n{'='*60}")
    print("📊 TESTING PREDICTIONS ACCESS")
    print(f"{'='*60}")
    
    # First, get companies to test predictions with
    super_admin_token = tokens.get("super_admin")
    if not super_admin_token:
        print("❌ No super admin token available for company lookup")
        return
    
    companies_response = requests.get(
        f"{BASE_URL}/api/v1/companies/",
        headers={"Authorization": f"Bearer {super_admin_token}"}
    )
    
    if companies_response.status_code != 200:
        print("❌ Could not fetch companies for prediction testing")
        return
    
    companies = companies_response.json().get("companies", [])
    if not companies:
        print("❌ No companies available for prediction testing")
        return
    
    test_company_symbol = companies[0]["symbol"]
    print(f"🏭 Using company: {test_company_symbol}")
    
    # Test annual prediction creation
    test_prediction = {
        "stock_symbol": test_company_symbol,
        "reporting_year": "2024",
        "long_term_debt_to_total_capital": 0.25,
        "total_debt_to_ebitda": 2.5,
        "net_income_margin": 0.15,
        "ebit_to_interest_expense": 8.5,
        "return_on_assets": 0.12
    }
    
    for role, token in tokens.items():
        print(f"\n📈 Testing annual prediction creation as {role}...")
        
        # Modify year to avoid conflicts
        test_prediction["reporting_year"] = f"202{len(role)}"
        
        response = requests.post(
            f"{BASE_URL}/api/v1/predictions/annual",
            json=test_prediction,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Prediction creation successful")
            print(f"   📊 Default Probability: {data.get('prediction', {}).get('probability', 'Unknown')}")
        else:
            print(f"   ❌ Prediction creation failed: {response.status_code}")
            print(f"   📝 Response: {response.text}")

def main():
    """Run all tests"""
    print("🚀 TESTING ROLE-BASED ACCESS CONTROL SYSTEM")
    print("="*60)
    
    # Test authentication
    tokens = test_authentication()
    
    if not tokens:
        print("❌ No tokens available, cannot continue testing")
        return
    
    # Test company creation permissions
    test_company_creation(tokens)
    
    # Test organization access
    test_organization_access(tokens)
    
    # Test predictions access
    test_predictions_access(tokens)
    
    print(f"\n{'='*60}")
    print("✅ ROLE SYSTEM TESTING COMPLETED")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
