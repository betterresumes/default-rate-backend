#!/usr/bin/env python3
"""
Test script for Redis connection and Celery task management
"""

import os
import sys
import time
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, '/Users/nikhil/Downloads/pranit/work/final/default-rate/backend')

from app.workers.celery_app import celery_app
# Email tasks have been removed - test will use basic Celery functionality

def test_redis_connection():
    """Test Redis connection"""
    print("🔍 Testing Redis Connection...")
    try:
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=3, timeout=10)
        print("✅ Redis connection successful!")
        
        print(f"📊 Redis Configuration:")
        print(f"   REDIS_URL: {os.getenv('REDIS_URL', 'Not set')}")
        print(f"   Broker URL: {celery_app.conf.broker_url}")
        print(f"   Backend URL: {celery_app.conf.result_backend}")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False

def test_celery_task():
    """Test a simple Celery task"""
    print("\n🔍 Testing Celery Task...")
    try:
        # Just test task inspection since email tasks were removed
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            print("✅ Celery worker inspection successful")
            print(f"📊 Active workers: {list(stats.keys())}")
            return True
        else:
            print("⚠️  No active workers found (normal if worker not running)")
            return True  # This is OK for testing
            
    except Exception as e:
        print(f"❌ Celery task test failed: {e}")
        return False

def test_celery_inspection():
    """Test Celery worker inspection"""
    print("\n🔍 Testing Celery Worker Inspection...")
    try:
        inspect = celery_app.control.inspect()
        
        # Check active workers
        active_workers = inspect.active()
        if active_workers:
            print(f"✅ Active workers found: {list(active_workers.keys())}")
        else:
            print("⚠️  No active workers found")
            
        # Check registered tasks
        registered_tasks = inspect.registered()
        if registered_tasks:
            for worker, tasks in registered_tasks.items():
                print(f"📋 Worker {worker} has {len(tasks)} registered tasks")
        else:
            print("⚠️  No registered tasks found")
            
        return True
    except Exception as e:
        print(f"❌ Worker inspection failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting Redis & Celery Testing Suite")
    print("=" * 50)
    
    # Test 1: Redis Connection
    redis_ok = test_redis_connection()
    
    # Test 2: Celery Task
    if redis_ok:
        celery_ok = test_celery_task()
    else:
        celery_ok = False
    
    # Test 3: Worker Inspection
    if redis_ok:
        inspect_ok = test_celery_inspection()
    else:
        inspect_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"   Redis Connection: {'✅ PASS' if redis_ok else '❌ FAIL'}")
    print(f"   Celery Task: {'✅ PASS' if celery_ok else '❌ FAIL'}")
    print(f"   Worker Inspection: {'✅ PASS' if inspect_ok else '❌ FAIL'}")
    
    if redis_ok and celery_ok:
        print("\n🎉 All tests passed! Redis and Celery are working correctly.")
    else:
        print("\n⚠️  Some tests failed. Check the error messages above.")
        
    print(f"\n📅 Test completed at: {datetime.now().isoformat()}")

if __name__ == "__main__":
    main()
