#!/usr/bin/env python3
"""
Test script to verify Celery is working properly after fixing the serialization issue
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.workers.celery_app import celery_app

def test_celery_connection():
    """Test basic Celery connection"""
    try:
        # Test broker connection
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            print("✅ Celery broker connection successful")
            print(f"Active workers: {list(stats.keys())}")
            return True
        else:
            print("❌ No active workers found")
            return False
            
    except Exception as e:
        print(f"❌ Celery connection failed: {e}")
        return False

def test_task_registry():
    """Test if tasks are properly registered"""
    try:
        tasks = celery_app.tasks
        print(f"✅ Registered tasks ({len(tasks)}):")
        for task_name in sorted(tasks.keys()):
            if not task_name.startswith('celery.'):
                print(f"  - {task_name}")
        return True
    except Exception as e:
        print(f"❌ Task registry check failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Celery configuration after fixes...")
    print()
    
    # Test connection
    connection_ok = test_celery_connection()
    print()
    
    # Test task registry
    registry_ok = test_task_registry()
    print()
    
    if connection_ok and registry_ok:
        print("🎉 Celery setup looks good! You should now be able to start the worker without errors.")
    else:
        print("⚠️  There are still some issues with the Celery setup.")
