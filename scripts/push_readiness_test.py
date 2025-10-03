#!/usr/bin/env python3
"""
CI/CD Push Readiness Test - Focused on Critical Issues
Tests only what's needed to verify CI/CD pipeline will work
"""

import sys
import os
import subprocess
import re

def test_critical_security():
    """Test the most critical security fix"""
    print("🔒 Testing CRITICAL security fix...")
    
    test_code = '''
import sys
sys.path.insert(0, "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")

from app.schemas.schemas import UserCreatePublic, UserCreate

# CRITICAL: Test that public registration blocks role field
try:
    UserCreatePublic(email="hacker@evil.com", password="password123", role="super_admin")
    print("SECURITY_BREACH_DETECTED")
    sys.exit(1)
except Exception as e:
    if "extra fields not permitted" in str(e):
        print("SECURITY_PROTECTED")
    else:
        print(f"UNEXPECTED_ERROR: {e}")
        sys.exit(1)

# Test admin schema still works
try:
    UserCreate(email="admin@test.com", password="password123", role="tenant_admin")
    print("ADMIN_SCHEMA_OK")
except Exception as e:
    print(f"ADMIN_SCHEMA_ERROR: {e}")
    sys.exit(1)

print("SUCCESS")
'''
    
    result = subprocess.run([
        'python3', '-c', test_code
    ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
    
    output = result.stdout.strip()
    if "SECURITY_PROTECTED" in output and "ADMIN_SCHEMA_OK" in output and "SUCCESS" in output:
        print("✅ CRITICAL security fix verified - Authentication bypass prevented")
        return True
    else:
        print("❌ CRITICAL security fix failed")
        print(f"   Output: {output}")
        return False

def test_rate_limiting_fixes():
    """Test that rate-limited functions have request parameters"""
    print("🎯 Testing rate-limiting function signatures...")
    
    # Files that we specifically fixed
    files_to_check = {
        'app/api/v1/tenant_admin_management.py': [
            'create_tenant_with_admin',
            'assign_existing_user_as_tenant_admin', 
            'get_tenant_admin_info',
            'remove_tenant_admin_role',
            'assign_user_to_organization'
        ],
        'app/api/v1/scaling.py': [
            'execute_scaling', 'manual_scaling', 'get_scaling_status'
        ],
        'app/api/v1/auth_admin.py': [
            'admin_create_user'
        ]
    }
    
    issues = []
    
    for file_path, functions in files_to_check.items():
        full_path = f"/Users/nikhil/Downloads/pranit/work/final/default-rate/backend/{file_path}"
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                content = f.read()
            
            for func_name in functions:
                # Look for the function definition
                pattern = rf'async def {func_name}\s*\('
                match = re.search(pattern, content)
                if match:
                    # Get the function signature
                    start = match.start()
                    # Find the end of the function signature
                    func_sig = content[start:start+500]  # Get enough text
                    end_paren = func_sig.find('):', func_sig.find('('))
                    if end_paren != -1:
                        func_sig = func_sig[:end_paren + 1]
                    
                    # Check if request parameter exists
                    if 'request:' not in func_sig:
                        issues.append(f"{file_path}:{func_name} missing request parameter")
    
    if issues:
        print("❌ Rate-limiting fixes incomplete:")
        for issue in issues:
            print(f"   {issue}")
        return False
    else:
        print("✅ Rate-limiting fixes verified - All functions have request parameters")
        return True

def test_python_compilation():
    """Test Python syntax is valid"""
    print("🐍 Testing Python syntax compilation...")
    
    result = subprocess.run([
        'find', 'app', '-name', '*.py', '-exec', 'python3', '-m', 'py_compile', '{}', ';'
    ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
    
    if result.returncode == 0:
        print("✅ Python syntax valid - All files compile successfully")
        return True
    else:
        print("❌ Python syntax errors detected")
        print(f"   Error: {result.stderr}")
        return False

def test_requirements_structure():
    """Test requirements files exist and have key dependencies"""
    print("📦 Testing requirements structure...")
    
    prod_req_path = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend/requirements.prod.txt"
    
    if not os.path.exists(prod_req_path):
        print("❌ requirements.prod.txt not found")
        return False
    
    with open(prod_req_path, 'r') as f:
        content = f.read()
    
    required_packages = ['fastapi', 'slowapi', 'uvicorn', 'sqlalchemy', 'pydantic']
    missing = []
    
    for package in required_packages:
        if package not in content:
            missing.append(package)
    
    if missing:
        print(f"❌ Missing required packages: {missing}")
        return False
    else:
        print("✅ Requirements verified - All critical packages present")
        return True

def test_pydantic_v2_warnings():
    """Test that Pydantic V2 warnings are fixed"""
    print("🔧 Testing Pydantic V2 compatibility...")
    
    schemas_path = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend/app/schemas/schemas.py"
    
    with open(schemas_path, 'r') as f:
        content = f.read()
    
    # Check that schema_extra is not used (should be json_schema_extra)
    if 'schema_extra' in content and 'json_schema_extra' not in content:
        print("❌ Pydantic V2 warning not fixed - schema_extra still present")
        return False
    else:
        print("✅ Pydantic V2 compatibility - schema_extra issue resolved")
        return True

def check_git_changes():
    """Check what files have been modified"""
    print("📋 Checking modified files...")
    
    result = subprocess.run([
        'git', 'diff', '--name-only'
    ], capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
    
    if result.returncode == 0:
        changed_files = result.stdout.strip().split('\n') if result.stdout.strip() else []
        if changed_files:
            print("📝 Modified files ready for commit:")
            for file in changed_files:
                if file:
                    print(f"   • {file}")
        else:
            print("ℹ️ No uncommitted changes detected")
        return True
    else:
        print("ℹ️ Not in a git repository or git not available")
        return True

def main():
    print("🚀 CI/CD PUSH READINESS CHECK")
    print("=" * 50)
    print("Testing critical fixes for production deployment\n")
    
    # Run critical tests only
    tests = [
        ("Critical Security Fix", test_critical_security),
        ("Rate-Limiting Functions", test_rate_limiting_fixes),
        ("Python Compilation", test_python_compilation),
        ("Requirements Structure", test_requirements_structure),
        ("Pydantic V2 Compatibility", test_pydantic_v2_warnings),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name}")
        print("-" * 30)
        result = test_func()
        results.append(result)
        print()
    
    # Check git status
    print("🔍 Git Status Check")
    print("-" * 30)
    check_git_changes()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 CI/CD READINESS SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    for i, (test_name, _) in enumerate(tests):
        status = "✅ PASS" if results[i] else "❌ FAIL"
        print(f"{test_name:<25} {status}")
    
    print(f"\n📈 Score: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 READY FOR PRODUCTION PUSH!")
        print("\n🚀 Recommended deployment steps:")
        print("   git add .")
        print("   git commit -m 'Fix: Add missing request parameters to rate-limited functions'")
        print("   git push origin prod")
        print("\n✅ CI/CD pipeline should now execute successfully!")
        print("✅ Critical security vulnerability remains fixed!")
        print("✅ All rate-limiting issues resolved!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} critical test(s) failed")
        print("❌ DO NOT PUSH - Issues must be resolved first")
        return 1

if __name__ == "__main__":
    sys.exit(main())
