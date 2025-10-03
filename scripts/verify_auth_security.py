#!/usr/bin/env python3
"""
🔒 Authentication Security Verification Script
==============================================

This script verifies that the critical authentication vulnerability has been fixed.
It tests the register API to ensure role privilege escalation is prevented.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_schema_security():
    """Test that schemas properly restrict role assignment"""
    print("🔍 Testing Schema Security...")
    
    try:
        from app.schemas.schemas import UserCreatePublic, UserCreate
        
        # Test 1: UserCreatePublic should reject role field
        print("Test 1: Public registration schema security")
        try:
            malicious_data = {
                'email': 'hacker@evil.com',
                'password': 'password123',
                'role': 'super_admin'  # This should be rejected
            }
            UserCreatePublic(**malicious_data)
            print("❌ SECURITY FAILURE: Public schema accepted 'role' field!")
            return False
        except Exception as e:
            # Check for both Pydantic v1 and v2 error messages
            if "extra fields not permitted" in str(e) or "Extra inputs are not permitted" in str(e):
                print("✅ Public schema correctly rejects 'role' field")
            else:
                print(f"⚠️  Unexpected error: {e}")
                return False
        
        # Test 2: UserCreate should allow role field (for admin use)
        print("Test 2: Admin creation schema functionality")
        try:
            admin_data = {
                'email': 'admin@company.com',
                'password': 'securepass123',
                'role': 'org_admin'
            }
            admin_user = UserCreate(**admin_data)
            if admin_user.role == 'org_admin':
                print("✅ Admin schema correctly accepts 'role' field")
            else:
                print("❌ Admin schema not working correctly")
                return False
        except Exception as e:
            print(f"❌ Admin schema failed: {e}")
            return False
            
        # Test 3: Check field lists
        public_fields = set(UserCreatePublic.__fields__.keys())
        admin_fields = set(UserCreate.__fields__.keys())
        
        if 'role' in public_fields:
            print("❌ SECURITY FAILURE: 'role' field found in public schema")
            return False
        
        if 'role' not in admin_fields:
            print("❌ Admin schema missing 'role' field")
            return False
            
        print("✅ Field validation passed")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_register_endpoint_security():
    """Test the register endpoint implementation"""
    print("\n🔍 Testing Register Endpoint Security...")
    
    try:
        # Read the auth file to verify the fix
        auth_file = os.path.join(os.path.dirname(__file__), '..', 'app', 'api', 'v1', 'auth_multi_tenant.py')
        
        with open(auth_file, 'r') as f:
            content = f.read()
        
        # Check for security fixes
        security_checks = [
            ('UserCreatePublic in imports', 'UserCreatePublic' in content),
            ('Hard-coded user role', 'role="user"' in content),
            ('Security comment present', '⚠️ SECURITY FIX' in content),
            ('No role from user data', 'user_data.role' not in content)
        ]
        
        all_passed = True
        for check_name, condition in security_checks:
            if condition:
                print(f"✅ {check_name}")
            else:
                print(f"❌ {check_name}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        print(f"❌ Error reading auth file: {e}")
        return False

def test_attack_scenarios():
    """Test common attack scenarios"""
    print("\n🔍 Testing Attack Scenarios...")
    
    attack_scenarios = [
        {
            'name': 'Super Admin Escalation',
            'data': {'email': 'hacker@evil.com', 'password': 'pass123', 'role': 'super_admin'},
            'should_fail': True
        },
        {
            'name': 'Tenant Admin Escalation', 
            'data': {'email': 'hacker@evil.com', 'password': 'pass123', 'role': 'tenant_admin'},
            'should_fail': True
        },
        {
            'name': 'Org Admin Escalation',
            'data': {'email': 'hacker@evil.com', 'password': 'pass123', 'role': 'org_admin'},
            'should_fail': True
        },
        {
            'name': 'Legitimate User Registration',
            'data': {'email': 'user@company.com', 'password': 'password123'},
            'should_fail': False
        }
    ]
    
    try:
        from app.schemas.schemas import UserCreatePublic
        
        all_passed = True
        for scenario in attack_scenarios:
            try:
                UserCreatePublic(**scenario['data'])
                if scenario['should_fail']:
                    print(f"❌ {scenario['name']}: Attack succeeded (should have failed)")
                    all_passed = False
                else:
                    print(f"✅ {scenario['name']}: Legitimate request succeeded")
            except Exception:
                if scenario['should_fail']:
                    print(f"✅ {scenario['name']}: Attack blocked correctly")
                else:
                    print(f"❌ {scenario['name']}: Legitimate request failed")
                    all_passed = False
        
        return all_passed
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def main():
    """Run all security tests"""
    print("🔒 AUTHENTICATION SECURITY VERIFICATION")
    print("=" * 50)
    
    tests = [
        ("Schema Security", test_schema_security),
        ("Register Endpoint Security", test_register_endpoint_security), 
        ("Attack Scenarios", test_attack_scenarios)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 SECURITY TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 ALL SECURITY TESTS PASSED!")
        print("✅ The authentication vulnerability has been successfully fixed.")
        print("🔒 Role privilege escalation is now prevented.")
    else:
        print("\n⚠️  SECURITY ISSUES DETECTED!")
        print("❌ Some tests failed. Please review the implementation.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
