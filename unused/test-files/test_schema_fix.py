#!/usr/bin/env python3
"""
Test script to verify the updated code uses access_level instead of is_global
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Company, AnnualPrediction, QuarterlyPrediction

def test_database_schema():
    """Test that the database models have the correct fields"""
    print("🔍 Testing database schema...")
    
    # Check Company model
    company_fields = [attr for attr in dir(Company) if not attr.startswith('_')]
    print(f"✅ Company fields: {[f for f in company_fields if f in ['access_level', 'is_global']]}")
    
    if 'access_level' in company_fields and 'is_global' not in company_fields:
        print("✅ Company model uses access_level (correct)")
    else:
        print("❌ Company model schema issue")
    
    # Check AnnualPrediction model
    annual_fields = [attr for attr in dir(AnnualPrediction) if not attr.startswith('_')]
    if 'access_level' in annual_fields:
        print("✅ AnnualPrediction model has access_level")
    else:
        print("❌ AnnualPrediction model missing access_level")
    
    # Check QuarterlyPrediction model
    quarterly_fields = [attr for attr in dir(QuarterlyPrediction) if not attr.startswith('_')]
    if 'access_level' in quarterly_fields:
        print("✅ QuarterlyPrediction model has access_level")
    else:
        print("❌ QuarterlyPrediction model missing access_level")

def test_task_logic():
    """Test the task logic without database operations"""
    print("\n🧪 Testing task access level logic...")
    
    # Test cases
    test_cases = [
        {"organization_id": "org-123", "user_role": "org_admin", "expected": "organization"},
        {"organization_id": None, "user_role": "super_admin", "expected": "system"},
        {"organization_id": None, "user_role": "user", "expected": "personal"}
    ]
    
    for case in test_cases:
        organization_id = case["organization_id"]
        user_role = case["user_role"]
        expected = case["expected"]
        
        # Simulate the logic from create_or_get_company
        if organization_id:
            access_level = "organization"
        else:
            if user_role == "super_admin":
                access_level = "system"
            else:
                access_level = "personal"
        
        result = "✅" if access_level == expected else "❌"
        print(f"{result} {user_role} with org_id={organization_id} -> {access_level} (expected: {expected})")

if __name__ == "__main__":
    print("🔧 Testing updated schema and logic...\n")
    
    try:
        test_database_schema()
        test_task_logic()
        print("\n🎉 Schema and logic tests completed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
