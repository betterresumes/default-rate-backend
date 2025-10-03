#!/usr/bin/env python3
"""
Production-Ready CI/CD Test Suite
Comprehensive simulation of GitHub Actions pipeline
"""

import sys
import os
import subprocess
import tempfile
import json

def test_python_syntax():
    """Test Python syntax across all files"""
    print("🔍 Testing Python syntax validation...")
    
    result = subprocess.run([
        'find', 'app', '-name', '*.py', '-exec', 'python3', '-m', 'py_compile', '{}', ';'
    ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
    
    if result.returncode == 0:
        print("✅ Python syntax validation - PASSED")
        return True
    else:
        print("❌ Python syntax validation - FAILED")
        print(f"   Error: {result.stderr}")
        return False

def test_requirements_compatibility():
    """Test that requirements can be processed"""
    print("🔍 Testing requirements files...")
    
    req_files = ['requirements.txt', 'requirements.prod.txt']
    for req_file in req_files:
        path = f"/Users/nikhil/Downloads/pranit/work/final/default-rate/backend/{req_file}"
        if os.path.exists(path):
            with open(path, 'r') as f:
                content = f.read()
                if 'slowapi' in content and 'fastapi' in content:
                    print(f"✅ {req_file} contains required packages")
                else:
                    print(f"❌ {req_file} missing required packages")
                    return False
        else:
            print(f"⚠️ {req_file} not found")
    
    return True

def test_security_schemas():
    """Test critical security fixes"""
    print("🔍 Testing authentication security...")
    
    test_code = '''
import sys
sys.path.insert(0, "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")

try:
    from app.schemas.schemas import UserCreatePublic, UserCreate
    
    # Test 1: Public schema rejects role field (CRITICAL SECURITY)
    try:
        UserCreatePublic(email="hacker@evil.com", password="password123", role="super_admin")
        print("SECURITY_BREACH")
        sys.exit(1)
    except Exception as e:
        if "extra fields not permitted" in str(e):
            print("SECURITY_OK")
        else:
            print(f"SECURITY_ERROR: {e}")
            sys.exit(1)
    
    # Test 2: Admin schema accepts role field
    try:
        UserCreate(email="admin@test.com", password="password123", role="tenant_admin")
        print("ADMIN_OK")
    except Exception as e:
        print(f"ADMIN_ERROR: {e}")
        sys.exit(1)
        
    print("SUCCESS")
    
except Exception as e:
    print(f"IMPORT_ERROR: {e}")
    sys.exit(1)
'''
    
    result = subprocess.run([
        'python3', '-c', test_code
    ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
    
    output = result.stdout.strip()
    if "SECURITY_OK" in output and "ADMIN_OK" in output and "SUCCESS" in output:
        print("✅ Authentication security - VERIFIED")
        return True
    else:
        print("❌ Authentication security - FAILED")
        print(f"   Output: {output}")
        if result.stderr:
            print(f"   Error: {result.stderr}")
        return False

def test_rate_limiting_parameters():
    """Test that all rate-limited functions have proper parameters"""
    print("🔍 Testing rate-limiting function signatures...")
    
    # Run our detection script
    result = subprocess.run([
        'python3', 'scripts/find_missing_request_params.py'
    ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
    
    if result.returncode == 0 and "No issues found" in result.stdout:
        print("✅ Rate-limiting parameters - VERIFIED")
        return True
    else:
        print("❌ Rate-limiting parameters - FAILED")
        print(f"   Output: {result.stdout}")
        if result.stderr:
            print(f"   Error: {result.stderr}")
        return False

def test_app_structure_mock_slowapi():
    """Test app structure with mocked slowapi (simulates CI environment)"""
    print("🔍 Testing app structure with mocked dependencies...")
    
    test_script = '''
import sys
import os
from unittest.mock import MagicMock, patch

# Add project to path
sys.path.insert(0, "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")

# Mock slowapi before any imports
slowapi_mock = MagicMock()
slowapi_mock.Limiter = MagicMock()
slowapi_mock._rate_limit_exceeded_handler = MagicMock()

# Create a mock limiter that returns a pass-through decorator
def mock_limiter_func(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

slowapi_mock.Limiter.return_value.limit = mock_limiter_func
sys.modules['slowapi'] = slowapi_mock

try:
    # Test specific imports that were failing
    from app.api.v1.tenant_admin_management import create_tenant_with_admin
    print("TENANT_ADMIN_OK")
    
    from app.api.v1.scaling import execute_scaling
    print("SCALING_OK")
    
    from app.api.v1.auth_admin import admin_create_user
    print("AUTH_ADMIN_OK")
    
    # Test that functions have request parameter
    import inspect
    
    sig = inspect.signature(create_tenant_with_admin)
    if 'request' in sig.parameters:
        print("TENANT_PARAMS_OK")
    else:
        print("TENANT_PARAMS_FAIL")
        sys.exit(1)
    
    sig = inspect.signature(execute_scaling)  
    if 'request' in sig.parameters:
        print("SCALING_PARAMS_OK")
    else:
        print("SCALING_PARAMS_FAIL")
        sys.exit(1)
    
    sig = inspect.signature(admin_create_user)
    if 'request' in sig.parameters:
        print("AUTH_PARAMS_OK")
    else:
        print("AUTH_PARAMS_FAIL")
        sys.exit(1)
    
    print("ALL_IMPORTS_SUCCESS")
    
except Exception as e:
    print(f"IMPORT_FAIL: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        temp_file = f.name
    
    try:
        result = subprocess.run([
            'python3', temp_file
        ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
        
        output = result.stdout.strip()
        expected_outputs = [
            "TENANT_ADMIN_OK", "SCALING_OK", "AUTH_ADMIN_OK",
            "TENANT_PARAMS_OK", "SCALING_PARAMS_OK", "AUTH_PARAMS_OK", 
            "ALL_IMPORTS_SUCCESS"
        ]
        
        if all(expected in output for expected in expected_outputs):
            print("✅ App structure with mocked dependencies - PASSED")
            return True
        else:
            print("❌ App structure with mocked dependencies - FAILED")
            print(f"   Output: {output}")
            if result.stderr:
                print(f"   Error: {result.stderr}")
            return False
            
    finally:
        os.unlink(temp_file)

def test_dockerfile_compatibility():
    """Test that Dockerfile exists and looks correct"""
    print("🔍 Testing Docker configuration...")
    
    dockerfile_path = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend/Dockerfile"
    if os.path.exists(dockerfile_path):
        with open(dockerfile_path, 'r') as f:
            content = f.read()
            if 'requirements' in content and 'python' in content.lower():
                print("✅ Dockerfile - VALID")
                return True
            else:
                print("❌ Dockerfile - INVALID CONTENT")
                return False
    else:
        print("❌ Dockerfile - NOT FOUND")
        return False

def test_git_status():
    """Check git status for deployment readiness"""
    print("🔍 Checking git status...")
    
    # Check if we're in a git repository
    result = subprocess.run([
        'git', 'status', '--porcelain'
    ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
    
    if result.returncode == 0:
        if result.stdout.strip():
            print("⚠️ Git status - UNCOMMITTED CHANGES")
            print("   You have uncommitted changes. Consider committing before deployment.")
            print(f"   Changes: {result.stdout.strip()[:200]}...")
        else:
            print("✅ Git status - CLEAN")
        return True
    else:
        print("⚠️ Git status - NOT A GIT REPO or ERROR")
        return True  # Don't fail the test for this

def main():
    print("🚀 COMPREHENSIVE CI/CD READINESS TEST")
    print("=" * 60)
    print("Simulating complete GitHub Actions pipeline...\n")
    
    tests = [
        ("Python Syntax", test_python_syntax),
        ("Requirements", test_requirements_compatibility),
        ("Security Schemas", test_security_schemas),
        ("Rate Limiting", test_rate_limiting_parameters),
        ("App Structure", test_app_structure_mock_slowapi),
        ("Docker Config", test_dockerfile_compatibility),
        ("Git Status", test_git_status),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running {test_name} Test...")
        print("-" * 40)
        result = test_func()
        results.append((test_name, result))
        print()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 CI/CD READINESS REPORT")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:<20} {status}")
        if result:
            passed += 1
    
    total = len(results)
    print(f"\n📈 Score: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 CI/CD PIPELINE READY!")
        print("✅ ALL SYSTEMS GO - SAFE TO PUSH TO PRODUCTION")
        print("\n🚀 Deployment Instructions:")
        print("   1. git add .")
        print("   2. git commit -m 'Fix CI/CD: Add missing request parameters to rate-limited functions'")
        print("   3. git push origin prod")
        print("   4. Monitor CI/CD pipeline for successful deployment")
        return 0
    else:
        print(f"\n⚠️ CI/CD ISSUES DETECTED")
        print(f"   {total - passed} test(s) failed")
        print("   Please resolve issues before pushing to production")
        return 1

if __name__ == "__main__":
    sys.exit(main())
