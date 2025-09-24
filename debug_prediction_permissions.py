#!/usr/bin/env python3
"""
Debug script to check prediction permissions for a specific prediction ID
"""
import requests
import sys
import json

def check_prediction_details(prediction_id, token):
    """Check prediction details and permission logic"""
    
    # Base URL
    base_url = "http://localhost:8000/api/v1"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"🔍 Checking prediction: {prediction_id}")
    print("=" * 60)
    
    # 1. First, let's check if we can get the prediction details
    try:
        response = requests.get(f"{base_url}/predictions/annual", 
                              headers=headers, 
                              params={"page": 1, "size": 100})
        
        if response.status_code == 200:
            data = response.json()
            predictions = data.get("predictions", [])
            
            # Find our specific prediction
            target_prediction = None
            for pred in predictions:
                if pred["id"] == prediction_id:
                    target_prediction = pred
                    break
            
            if target_prediction:
                print("✅ Prediction found in user's accessible predictions:")
                print(f"   📝 ID: {target_prediction['id']}")
                print(f"   🏢 Company: {target_prediction['company_name']} ({target_prediction['company_symbol']})")
                print(f"   🔒 Access Level: {target_prediction['access_level']}")
                print(f"   👤 Created By: {target_prediction['created_by']}")
                print(f"   📧 Creator Email: {target_prediction.get('created_by_email', 'N/A')}")
                print(f"   🏛️ Organization: {target_prediction.get('organization_name', 'N/A')}")
                
                return target_prediction
            else:
                print("❌ Prediction not found in user's accessible predictions")
                print("   This could mean:")
                print("   1. The prediction doesn't exist")
                print("   2. The user doesn't have permission to view it")
                print("   3. It's a system-level prediction")
                return None
                
        else:
            print(f"❌ Failed to get predictions: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error checking prediction: {str(e)}")
        return None

def test_update_permission(prediction_id, token):
    """Test update permission with a sample request"""
    
    base_url = "http://localhost:8000/api/v1"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Sample update data
    update_data = {
        "company_name": "Test Company Update",
        "company_symbol": "TEST",
        "market_cap": 1000000000,
        "sector": "Technology",
        "reporting_year": "2024",
        "reporting_quarter": None,
        "long_term_debt_to_total_capital": 0.25,
        "total_debt_to_ebitda": 1.5,
        "net_income_margin": 0.15,
        "ebit_to_interest_expense": 12.0,
        "return_on_assets": 0.08
    }
    
    print(f"\n🔧 Testing UPDATE permission for: {prediction_id}")
    print("-" * 40)
    
    try:
        response = requests.put(f"{base_url}/predictions/annual/{prediction_id}",
                               headers=headers,
                               json=update_data)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ UPDATE SUCCESSFUL - User can update this prediction")
            result = response.json()
            print(f"   Updated prediction ID: {result.get('prediction', {}).get('id', 'N/A')}")
        else:
            print("❌ UPDATE FAILED")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error testing update: {str(e)}")

def test_delete_permission(prediction_id, token):
    """Test delete permission (NOTE: This will actually delete if successful!)"""
    
    base_url = "http://localhost:8000/api/v1"
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"\n🗑️ Testing DELETE permission for: {prediction_id}")
    print("-" * 40)
    print("⚠️  WARNING: This will actually DELETE the prediction if successful!")
    print("   Comment out this function if you don't want to delete")
    
    # Uncomment the lines below to actually test delete
    """
    try:
        response = requests.delete(f"{base_url}/predictions/annual/{prediction_id}",
                                  headers=headers)
        
        print(f"📊 Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ DELETE SUCCESSFUL - User can delete this prediction")
            result = response.json()
            print(f"   Deleted prediction ID: {result.get('deleted_id', 'N/A')}")
        else:
            print("❌ DELETE FAILED")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('detail', 'Unknown error')}")
            except:
                print(f"   Raw response: {response.text}")
                
    except Exception as e:
        print(f"❌ Error testing delete: {str(e)}")
    """
    print("🛡️  DELETE test skipped to prevent accidental deletion")
    print("   Uncomment code in script to test actual deletion")

if __name__ == "__main__":
    # Configuration
    prediction_id = "47697e2c-60ce-4ddf-901f-00a3f3fa5e8b"
    
    # You need to provide your JWT token here
    token = input("Enter your JWT token: ").strip()
    
    if not token:
        print("❌ No token provided")
        sys.exit(1)
    
    print("🚀 Starting Prediction Permission Debug")
    print("=" * 60)
    
    # Check prediction details
    prediction_details = check_prediction_details(prediction_id, token)
    
    # Test update permission
    test_update_permission(prediction_id, token)
    
    # Test delete permission (disabled by default)
    test_delete_permission(prediction_id, token)
    
    print("\n" + "=" * 60)
    print("🏁 Debug complete!")
    
    if prediction_details:
        print(f"\n💡 Permission Analysis:")
        access_level = prediction_details.get('access_level', 'unknown')
        created_by = prediction_details.get('created_by', 'unknown')
        
        if access_level == 'system':
            print("   🔒 This is a SYSTEM-level prediction")
            print("   ➡️  Only super_admin can modify it")
        else:
            print(f"   🔓 This is a {access_level.upper()}-level prediction")
            print(f"   👤 Created by user ID: {created_by}")
            print("   ➡️  Creator or super_admin can modify it")
