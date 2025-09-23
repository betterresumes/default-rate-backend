#!/usr/bin/env python3
"""
Diagnostic script to identify Celery worker crash issues
"""

import os
import sys
import traceback
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # Load .env
load_dotenv('.env.local')  # Load .env.local (overrides .env)

def check_redis_connection():
    """Check Redis connection"""
    try:
        import redis
        
        # Get Redis config from env
        REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
        REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
        REDIS_DB = int(os.getenv("REDIS_DB", "0"))
        REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
        
        print(f"🔍 Testing Redis connection...")
        print(f"   Host: {REDIS_HOST}")
        print(f"   Port: {REDIS_PORT}")
        print(f"   DB: {REDIS_DB}")
        
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD if REDIS_PASSWORD else None,
            decode_responses=True
        )
        
        # Test connection
        r.ping()
        print("✅ Redis connection successful!")
        
        # Test basic operations
        r.set("test_key", "test_value", ex=10)
        result = r.get("test_key")
        if result == "test_value":
            print("✅ Redis read/write operations working!")
        else:
            print("⚠️ Redis read/write test failed!")
        
        return True
        
    except ImportError:
        print("❌ Redis module not installed! Run: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def check_database_connection():
    """Check database connection"""
    try:
        from app.core.database import get_session_local
        from sqlalchemy import text
        
        print("🔍 Testing database connection...")
        
        SessionLocal = get_session_local()
        db = SessionLocal()
        
        # Test query with proper text() wrapper
        result = db.execute(text("SELECT 1"))
        print("✅ Database connection successful!")
        
        db.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def check_ml_services():
    """Check ML services"""
    try:
        print("🔍 Testing ML services...")
        
        from app.services.ml_service import ml_model
        from app.services.quarterly_ml_service import quarterly_ml_model
        
        print("✅ ML services imported successfully!")
        
        # Test a simple prediction
        test_data = {
            'long_term_debt_to_total_capital': 0.3,
            'total_debt_to_ebitda': 2.5,
            'net_income_margin': 0.15,
            'ebit_to_interest_expense': 5.0,
            'return_on_assets': 0.08
        }
        
        # Note: Skip async ML test for now - just check imports
        print("⚠️ ML model testing skipped (requires async)")
        
        return True
        
    except Exception as e:
        print(f"❌ ML services failed: {e}")
        return False

def check_celery_imports():
    """Check Celery and worker imports"""
    try:
        print("🔍 Testing Celery imports...")
        
        from app.workers.celery_app import celery_app
        print("✅ Celery app imported!")
        
        from app.workers.tasks import process_annual_bulk_upload_task
        print("✅ Worker tasks imported!")
        
        from app.services.celery_bulk_upload_service import CeleryBulkUploadService
        print("✅ Bulk upload service imported!")
        
        return True
        
    except Exception as e:
        print(f"❌ Celery imports failed: {e}")
        traceback.print_exc()
        return False

def check_environment():
    """Check environment variables"""
    print("🔍 Checking environment variables...")
    
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY"
    ]
    
    optional_vars = [
        "REDIS_HOST",
        "REDIS_PORT", 
        "REDIS_DB",
        "REDIS_PASSWORD"
    ]
    
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * min(len(value), 10)}...")
        else:
            print(f"❌ {var}: Missing!")
            all_good = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️ {var}: Using default")
    
    return all_good

def check_file_structure():
    """Check file structure"""
    print("🔍 Checking file structure...")
    
    required_files = [
        "app/workers/celery_app.py",
        "app/workers/tasks.py", 
        "app/services/celery_bulk_upload_service.py",
        "app/services/ml_service.py",
        "app/services/quarterly_ml_service.py"
    ]
    
    all_good = True
    
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}: Missing!")
            all_good = False
    
    return all_good

def main():
    """Run all diagnostic checks"""
    print("🔧 Celery Worker Crash Diagnostic Tool")
    print("=" * 50)
    
    checks = [
        ("Environment Variables", check_environment),
        ("File Structure", check_file_structure),
        ("Redis Connection", check_redis_connection),
        ("Database Connection", check_database_connection),
        ("Celery Imports", check_celery_imports),
        # ("ML Services", check_ml_services)  # Skip async test for now
    ]
    
    results = {}
    
    for name, check_func in checks:
        print(f"\n📋 {name}")
        print("-" * 30)
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"❌ {name} check crashed: {e}")
            traceback.print_exc()
            results[name] = False
    
    print("\n" + "=" * 50)
    print("📊 Diagnostic Summary")
    print("=" * 50)
    
    for name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
    
    failed_checks = [name for name, success in results.items() if not success]
    
    if failed_checks:
        print(f"\n🚨 Issues found in: {', '.join(failed_checks)}")
        print("\n💡 Recommended fixes:")
        
        if "Redis Connection" in failed_checks:
            print("   1. Start Redis server: brew services start redis")
            print("   2. Or install Redis: brew install redis")
        
        if "Database Connection" in failed_checks:
            print("   3. Check DATABASE_URL in .env file")
            print("   4. Start PostgreSQL server")
        
        if "Celery Imports" in failed_checks:
            print("   5. Install missing dependencies: pip install -r requirements.txt")
            print("   6. Check for syntax errors in worker files")
        
        print("\n🔧 Quick fixes to try:")
        print("   • Restart Redis: brew services restart redis")
        print("   • Restart PostgreSQL: brew services restart postgresql")
        print("   • Clear Celery cache: celery -A app.workers.celery_app purge")
        print("   • Check logs: tail -f celery.log")
        
    else:
        print("\n✅ All checks passed! The issue might be:")
        print("   • Memory limits (try reducing worker concurrency)")
        print("   • Large file processing (try smaller test files)")  
        print("   • ML model loading issues")

if __name__ == "__main__":
    main()
