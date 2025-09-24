#!/usr/bin/env python3
"""
Test script to verify Celery configuration with Railway Redis URL
"""

import os
import sys

# Add the project root to the path
sys.path.insert(0, '/Users/nikhil/Downloads/pranit/work/final/default-rate/backend')

def test_railway_redis_config():
    """Test Railway Redis configuration"""
    print("🚂 Testing Railway Redis Configuration")
    print("=" * 50)
    
    # Simulate Railway environment
    test_redis_url = "redis://default:WKIFhoxBMxTwUgkrPoOdmDrPfyTvfbYB@redis.railway.internal:6379"
    os.environ['REDIS_URL'] = test_redis_url
    
    # Import after setting environment
    from app.workers.celery_app import celery_app
    
    print(f"✅ Celery configured with:")
    print(f"   Broker: {celery_app.conf.broker_url}")
    print(f"   Backend: {celery_app.conf.result_backend}")
    print(f"   Default Queue: {celery_app.conf.task_default_queue}")
    
    # Check task routes
    task_routes = celery_app.conf.task_routes
    print(f"\n📋 Task Routes ({len(task_routes)} configured):")
    for task, route in task_routes.items():
        queue = route.get('queue', 'default')
        task_name = task.split('.')[-1]
        print(f"   • {task_name} → {queue}")
    
    # Check if environment variables are properly overridden
    celery_broker = os.environ.get('CELERY_BROKER_URL', 'Not set')
    celery_backend = os.environ.get('CELERY_RESULT_BACKEND', 'Not set')
    
    print(f"\n🔧 Environment Variables:")
    print(f"   CELERY_BROKER_URL: {celery_broker}")
    print(f"   CELERY_RESULT_BACKEND: {celery_backend}")
    
    if 'railway.internal' in celery_broker and 'railway.internal' in celery_backend:
        print("✅ Railway Redis URLs properly set in environment variables!")
        return True
    else:
        print("⚠️  Environment variables not properly overridden")
        return False

def test_task_registration():
    """Test that tasks are properly registered"""
    from app.workers.celery_app import celery_app
    
    # Import tasks to ensure they're registered
    try:
        import app.workers.tasks
        print("✅ Tasks module imported successfully")
    except Exception as e:
        print(f"❌ Failed to import tasks: {e}")
        return False
    
    print(f"\n📋 Registered Tasks:")
    app_tasks = [t for t in celery_app.tasks.keys() if 'app.workers.tasks' in t]
    
    for task in sorted(app_tasks):
        task_name = task.split('.')[-1]
        print(f"   ✅ {task_name}")
    
    print(f"\nTotal registered tasks: {len(app_tasks)}")
    return len(app_tasks) > 0

if __name__ == "__main__":
    config_ok = test_railway_redis_config()
    tasks_ok = test_task_registration()
    
    print("\n" + "=" * 50)
    print("🏁 Railway Configuration Test Results:")
    print(f"   Railway Redis Config: {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"   Task Registration: {'✅ PASS' if tasks_ok else '❌ FAIL'}")
    
    if config_ok and tasks_ok:
        print("\n🎉 Railway Redis configuration is ready!")
        print("Your Celery worker should now connect properly to Railway Redis.")
    else:
        print("\n⚠️  Issues detected in configuration.")
