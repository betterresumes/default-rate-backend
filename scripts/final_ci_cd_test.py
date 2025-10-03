#!/usr/bin/env python3
"""
Final CI/CD Test - Simulates GitHub Actions Environment
Tests the exact conditions that caused the CI/CD failure
"""

import sys
import os
import subprocess
import tempfile

def test_app_import_with_mocked_slowapi():
    """Test app import with mocked slowapi like in CI environment"""
    print("🔍 Testing app import with mocked slowapi (CI simulation)...")
    
    # Create a temporary script that mocks slowapi
    test_script = '''
import sys
import os

# Add project root to path
project_root = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Mock slowapi to simulate CI environment where it might not be available
import types
from unittest.mock import MagicMock

# Create mock slowapi module
slowapi_mock = MagicMock()
slowapi_mock.Limiter = MagicMock()
slowapi_mock._rate_limit_exceeded_handler = MagicMock()

# Mock the Limiter class to return a no-op decorator
def mock_limiter(*args, **kwargs):
    def decorator(func):
        return func
    return decorator

slowapi_mock.Limiter.return_value.limit = mock_limiter
sys.modules["slowapi"] = slowapi_mock

# Now try to import the app
try:
    from app.main import app
    print("✅ App imports successfully with mocked slowapi")
    
    # Test that the app object exists
    if hasattr(app, "routes"):
        print(f"✅ App has {len(app.routes)} routes configured")
    
    # Test specific imports that were failing
    from app.api.v1.tenant_admin_management import router as tenant_admin_router
    print("✅ Tenant admin management imports successfully")
    
    from app.schemas.schemas import UserCreatePublic, UserCreate
    print("✅ Schemas import successfully")
    
    # Test security schema (most important fix)
    try:
        UserCreatePublic(email="test@test.com", password="password123", role="super_admin")
        print("❌ SECURITY FAILURE: Role field accepted!")
        sys.exit(1)
    except Exception as e:
        if "extra fields not permitted" in str(e):
            print("✅ SECURITY VERIFIED: Role field rejected")
        else:
            print(f"❌ Unexpected security error: {e}")
            sys.exit(1)
    
    print("\\n🎉 ALL TESTS PASSED - Ready for CI/CD deployment!")
    
except ImportError as e:
    if "slowapi" in str(e):
        print(f"❌ slowapi import error not properly mocked: {e}")
        sys.exit(1)
    else:
        print(f"❌ Unexpected import error: {e}")
        sys.exit(1)
except Exception as e:
    print(f"❌ App import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
'''
    
    try:
        # Write the test script to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            temp_file = f.name
        
        # Run the test script
        result = subprocess.run([
            sys.executable, temp_file
        ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
        
        # Clean up
        os.unlink(temp_file)
        
        if result.returncode == 0:
            print("✅ CI/CD simulation PASSED")
            print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print("❌ CI/CD simulation FAILED")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ CI/CD test error: {e}")
        return False

def test_rate_limiting_functions():
    """Test that all rate-limited functions have proper parameters"""
    print("\\n🔍 Testing rate-limited functions...")
    
    test_script = '''
import sys
import os
import ast
import inspect

# Add project root to path
project_root = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend"
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Files that should have rate-limited functions
files_to_check = [
    "app/api/v1/scaling.py",
    "app/api/v1/auth_admin.py", 
    "app/api/v1/tenant_admin_management.py"
]

issues = []

for file_path in files_to_check:
    full_path = os.path.join(project_root, file_path)
    if not os.path.exists(full_path):
        continue
        
    with open(full_path, 'r') as f:
        content = f.read()
    
    # Look for rate limit decorators
    lines = content.split('\\n')
    for i, line in enumerate(lines):
        if '@rate_limit' in line and not line.strip().startswith('#'):
            # Found a rate limit decorator, check the function signature on next lines
            func_start = i + 1
            while func_start < len(lines) and not lines[func_start].strip().startswith('async def'):
                func_start += 1
            
            if func_start < len(lines):
                func_line = lines[func_start].strip()
                # Get the function signature (may span multiple lines)
                func_sig = func_line
                j = func_start + 1
                while j < len(lines) and not func_sig.rstrip().endswith('):'):
                    func_sig += lines[j].strip()
                    j += 1
                
                # Check if 'request:' parameter is in the signature
                if 'request:' not in func_sig and 'request =' not in func_sig:
                    func_name = func_line.split('(')[0].replace('async def ', '')
                    issues.append(f"{file_path}:{func_start + 1} - {func_name} missing request parameter")

if issues:
    print("❌ Found rate-limiting issues:")
    for issue in issues:
        print(f"   {issue}")
    sys.exit(1)
else:
    print("✅ All rate-limited functions have request parameters")
'''
    
    try:
        result = subprocess.run([
            sys.executable, '-c', test_script
        ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
        
        if result.returncode == 0:
            print("✅ Rate limiting test PASSED")
            print(f"   {result.stdout.strip()}")
            return True
        else:
            print("❌ Rate limiting test FAILED")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            if result.stdout:
                print(f"   Output: {result.stdout.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ Rate limiting test error: {e}")
        return False

def main():
    print("🚀 FINAL CI/CD VERIFICATION")
    print("=" * 50)
    print("Testing fixes for the exact CI/CD failure reported\\n")
    
    results = []
    
    # Test 1: App import simulation
    results.append(test_app_import_with_mocked_slowapi())
    
    # Test 2: Rate limiting functions
    results.append(test_rate_limiting_functions())
    
    # Summary
    print("\\n" + "=" * 50)
    print("📊 FINAL TEST RESULTS")
    print("=" * 50)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("\\n✅ CI/CD READY FOR DEPLOYMENT!")
        print("\\n🔧 FIXES APPLIED:")
        print("   • Added 'request: Request' parameter to create_tenant_with_admin")
        print("   • Added 'request: Request' parameter to assign_existing_user_as_tenant_admin")
        print("   • Added 'request: Request' parameter to get_tenant_admin_info")
        print("   • Added 'request: Request' parameter to remove_tenant_admin_role")
        print("   • Added 'request: Request' parameter to assign_user_to_organization")
        print("   • Fixed Pydantic V2 warning (schema_extra → json_schema_extra)")
        print("   • Security vulnerability remains fixed (role field blocked)")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed ({passed}/{total} passed)")
        print("⚠️  Additional fixes needed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
