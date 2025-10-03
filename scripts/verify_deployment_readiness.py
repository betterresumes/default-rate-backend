#!/usr/bin/env python3
"""
🚀 Production Deployment Verification Script
==========================================

This script verifies that all security fixes are in place and the application
is ready for production deployment after the authentication bypass fix.
"""

import sys
import os
import subprocess

def run_command(command, description):
    """Run a command and return success status"""
    print(f"🔍 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout.strip():
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        print(f"   {line}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr.strip():
                for line in result.stderr.strip().split('\n'):
                    if line.strip():
                        print(f"   ERROR: {line}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def test_python_imports():
    """Test critical Python imports"""
    print("\n📦 Testing Application Structure...")
    
    tests = [
        ("python3 -c 'import app; print(\"App imports successfully\")'", "Core app import"),
        ("python3 -c 'from app.schemas.schemas import UserCreatePublic, UserCreate; print(\"Schemas import successfully\")'", "Schema imports"),
        ("python3 -c 'from app.schemas.schemas import UserCreatePublic; u = UserCreatePublic(email=\"test@test.com\", password=\"password123\"); print(\"UserCreatePublic validation works\")'", "Public schema validation"),
    ]
    
    results = []
    for command, description in tests:
        results.append(run_command(command, description))
    
    return all(results)

def test_security_fixes():
    """Test security vulnerability fixes"""
    print("\n🔒 Testing Security Fixes...")
    
    # Test that role escalation is prevented
    test_command = '''python3 -c "
from app.schemas.schemas import UserCreatePublic
try:
    UserCreatePublic(email='hacker@evil.com', password='pass123', role='super_admin')
    print('SECURITY FAILURE: Role accepted')
    exit(1)
except Exception as e:
    if 'extra fields not permitted' in str(e) or 'Extra inputs are not permitted' in str(e):
        print('Security verified: Role field rejected')
        exit(0)
    else:
        print(f'Unexpected error: {e}')
        exit(1)
"'''
    
    return run_command(test_command, "Role escalation prevention")

def test_auth_security_script():
    """Run the comprehensive authentication security test"""
    print("\n🛡️ Running Authentication Security Verification...")
    
    return run_command("python3 scripts/verify_auth_security.py", "Authentication security test suite")

def test_file_structure():
    """Verify all critical files exist"""
    print("\n📁 Verifying File Structure...")
    
    critical_files = [
        "app/main.py",
        "app/api/v1/auth_multi_tenant.py", 
        "app/schemas/schemas.py",
        "app/middleware/security_headers.py",
        "scripts/verify_auth_security.py",
        "docs/SECURITY_FIX_AUTH_BYPASS.md",
        "requirements.prod.txt",
        ".github/workflows/ci-cd.yml"
    ]
    
    all_exist = True
    for file_path in critical_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path} - EXISTS")
        else:
            print(f"❌ {file_path} - MISSING")
            all_exist = False
    
    return all_exist

def test_requirements():
    """Check that all required dependencies are present"""
    print("\n📋 Checking Requirements...")
    
    required_packages = [
        "fastapi",
        "uvicorn", 
        "sqlalchemy",
        "psycopg2-binary",
        "pydantic",
        "slowapi"  # For rate limiting
    ]
    
    try:
        with open("requirements.prod.txt", "r") as f:
            requirements_content = f.read().lower()
        
        all_present = True
        for package in required_packages:
            if package.lower() in requirements_content:
                print(f"✅ {package} - FOUND in requirements")
            else:
                print(f"❌ {package} - MISSING from requirements")
                all_present = False
        
        return all_present
    except Exception as e:
        print(f"❌ Error reading requirements.prod.txt: {e}")
        return False

def check_pydantic_v2_compatibility():
    """Check for Pydantic V2 compatibility"""
    print("\n🔧 Checking Pydantic V2 Compatibility...")
    
    # Check that orm_mode has been replaced with from_attributes
    try:
        with open("app/schemas/schemas.py", "r") as f:
            schema_content = f.read()
        
        if "orm_mode = True" in schema_content:
            print("❌ Old 'orm_mode = True' found - needs update to 'from_attributes = True'")
            return False
        
        if "from_attributes = True" in schema_content:
            print("✅ Pydantic V2 'from_attributes = True' found")
            return True
        
        print("⚠️ No Pydantic config found - may be OK")
        return True
        
    except Exception as e:
        print(f"❌ Error checking Pydantic compatibility: {e}")
        return False

def main():
    """Run all deployment verification tests"""
    print("🚀 PRODUCTION DEPLOYMENT VERIFICATION")
    print("=" * 50)
    print("Verifying authentication security fixes and deployment readiness...")
    
    test_functions = [
        ("File Structure", test_file_structure),
        ("Requirements", test_requirements),
        ("Pydantic V2 Compatibility", check_pydantic_v2_compatibility),
        ("Python Imports", test_python_imports),
        ("Security Fixes", test_security_fixes),
        ("Authentication Security", test_auth_security_script),
    ]
    
    results = []
    
    for test_name, test_func in test_functions:
        print(f"\n📋 Running {test_name} Tests...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with error: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 DEPLOYMENT VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {test_name}")
        if result:
            passed += 1
    
    success_rate = (passed / len(results)) * 100
    print(f"\nResults: {passed}/{len(results)} tests passed ({success_rate:.1f}%)")
    
    if passed == len(results):
        print("\n🎉 DEPLOYMENT VERIFICATION SUCCESSFUL!")
        print("✅ All security fixes are in place")
        print("✅ Authentication vulnerability has been resolved") 
        print("✅ Application is ready for production deployment")
        print("\n🚀 DEPLOY WITH CONFIDENCE!")
        return 0
    else:
        print("\n⚠️ DEPLOYMENT VERIFICATION FAILED!")
        print(f"❌ {len(results) - passed} test(s) failed")
        print("🔒 Do not deploy until all tests pass")
        return 1

if __name__ == "__main__":
    sys.exit(main())
