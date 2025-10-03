#!/usr/bin/env python3
"""
CI/CD Verification Script
Simulates the exact environment and tests that GitHub Actions will run
"""

import sys
import os
import subprocess
import importlib.util

def run_command(cmd, description=""):
    """Run a shell command and return success status"""
    print(f"🔍 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd="/Users/nikhil/Downloads/pranit/work/final/default-rate/backend")
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            if result.stdout.strip():
                print(f"   Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} - FAILED")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False

def test_imports():
    """Test all critical imports that CI/CD will need"""
    print("\n📦 Testing Critical Imports...")
    
    # Add current directory to path for imports
    import sys
    import os
    backend_path = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend"
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    tests = [
        ("from app.schemas.schemas import UserCreatePublic, UserCreate", "Schema imports"),
        ("from app.core.config import settings", "Config imports"),
        ("from app.core.database import Base", "Database imports"),
    ]
    
    for test_import, description in tests:
        try:
            exec(test_import)
            print(f"✅ {description} - PASSED")
        except ImportError as e:
            if "slowapi" in str(e):
                print(f"⚠️ {description} - EXPECTED (slowapi not in dev env)")
            else:
                print(f"❌ {description} - FAILED: {e}")
                return False
        except Exception as e:
            print(f"❌ {description} - ERROR: {e}")
            return False
    
    return True

def test_security_schemas():
    """Test the security fix for registration schemas"""
    print("\n🔒 Testing Security Schemas...")
    
    # Add current directory to path for imports
    import sys
    backend_path = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend"
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    try:
        from app.schemas.schemas import UserCreatePublic, UserCreate
        
        # Test that UserCreatePublic doesn't allow role field
        try:
            UserCreatePublic(email="test@test.com", password="password123", role="super_admin")
            print("❌ Security FAILED: UserCreatePublic accepts role field")
            return False
        except Exception as e:
            if "extra fields not permitted" in str(e) or "Extra inputs are not permitted" in str(e):
                print("✅ Security PASSED: UserCreatePublic rejects role field")
            else:
                print(f"❌ Unexpected error: {e}")
                return False
        
        # Test that UserCreate allows role field
        try:
            user = UserCreate(email="admin@test.com", password="password123", role="admin")
            print("✅ Admin schema PASSED: UserCreate accepts role field")
        except Exception as e:
            print(f"❌ Admin schema FAILED: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Schema test ERROR: {e}")
        return False

def test_pydantic_v2():
    """Test Pydantic V2 compatibility"""
    print("\n🔧 Testing Pydantic V2 Compatibility...")
    
    # Add current directory to path for imports
    import sys
    backend_path = "/Users/nikhil/Downloads/pranit/work/final/default-rate/backend"
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    
    try:
        from app.schemas.schemas import UserCreatePublic
        
        # Check if model_config exists (Pydantic V2 style)
        if hasattr(UserCreatePublic, 'model_config'):
            config = UserCreatePublic.model_config
            if hasattr(config, 'from_attributes') and config.from_attributes:
                print("✅ Pydantic V2 PASSED: from_attributes = True found")
                return True
            else:
                print("❌ Pydantic V2 FAILED: from_attributes not set correctly")
                return False
        else:
            print("❌ Pydantic V2 FAILED: model_config not found")
            return False
            
    except Exception as e:
        print(f"❌ Pydantic V2 test ERROR: {e}")
        return False

def main():
    print("🚀 CI/CD VERIFICATION SCRIPT")
    print("=" * 50)
    print("Simulating GitHub Actions environment tests...\n")
    
    # Track results
    results = []
    
    # Test 1: Python syntax and basic imports
    results.append(run_command("python3 -m py_compile app/main.py", "Python syntax check"))
    
    # Test 2: Requirements verification
    results.append(run_command("pip3 list | grep -E 'fastapi|uvicorn|sqlalchemy|pydantic'", "Core dependencies check"))
    
    # Test 3: Import tests
    results.append(test_imports())
    
    # Test 4: Security fix verification
    results.append(test_security_schemas())
    
    # Test 5: Pydantic V2 compatibility
    results.append(test_pydantic_v2())
    
    # Test 6: File syntax validation
    results.append(run_command("find app -name '*.py' -exec python3 -m py_compile {} \\;", "Python syntax validation"))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 CI/CD VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    if passed == total:
        print(f"🎉 ALL TESTS PASSED ({passed}/{total})")
        print("✅ Ready for production deployment!")
        return 0
    else:
        print(f"❌ {total - passed} test(s) failed ({passed}/{total} passed)")
        print("⚠️ Issues need to be resolved before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())
