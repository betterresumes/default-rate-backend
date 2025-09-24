#!/usr/bin/env python3
"""
Worker Configuration Analysis
"""
import sys
import os

# Add the app directory to Python path
sys.path.insert(0, '/Users/nikhil/Downloads/pranit/work/final/default-rate/backend')

try:
    from app.workers.celery_app import celery_app
    
    print("🔧 CURRENT CELERY WORKER CONFIGURATION")
    print("=" * 50)
    
    print(f"Platform: {sys.platform}")
    print(f"Worker Pool: {getattr(celery_app.conf, 'worker_pool', 'default')}")
    print(f"Worker Concurrency: {getattr(celery_app.conf, 'worker_concurrency', 'auto')}")
    
    # Check task routes
    task_routes = getattr(celery_app.conf, 'task_routes', {})
    print(f"\nTask Routes: {len(task_routes)} configured")
    
    if task_routes:
        queues = {}
        for task_pattern, route_config in task_routes.items():
            if isinstance(route_config, dict):
                queue = route_config.get('queue', 'default')
                if queue not in queues:
                    queues[queue] = []
                queues[queue].append(task_pattern)
        
        print("\nQueue Configuration:")
        for queue, tasks in queues.items():
            print(f"  📦 {queue}: {len(tasks)} task types")
            for task in tasks[:3]:  # Show first 3
                print(f"    - {task}")
            if len(tasks) > 3:
                print(f"    ... and {len(tasks) - 3} more")
    else:
        print("  ⚠️  All tasks use default queue (no separation)")
    
    # Check registered tasks
    registered_tasks = list(celery_app.tasks.keys())
    app_tasks = [t for t in registered_tasks if 'app.workers.tasks' in t]
    
    print(f"\nRegistered Tasks: {len(app_tasks)}")
    for task in sorted(app_tasks):
        task_name = task.split('.')[-1]
        print(f"  ✅ {task_name}")
    
    print("\n" + "=" * 50)
    print("CAPACITY ANALYSIS")
    print("=" * 50)
    
    # Determine current capacity
    if sys.platform == "darwin":  # macOS
        current_concurrency = 1  # Solo pool
        pool_type = "solo (single process)"
    else:  # Linux/Production
        current_concurrency = os.cpu_count() or 4
        pool_type = "prefork (multi-process)"
    
    print(f"Current Setup: {current_concurrency} concurrent tasks ({pool_type})")
    
    # Task processing estimates
    print("\nTASK PROCESSING CAPACITY (per hour):")
    print("📧 Email Tasks (1-3 sec each):")
    print(f"   Current: ~{current_concurrency * 1200}-{current_concurrency * 3600}")
    
    print("📊 Small Bulk Uploads (100 rows, 30-180 sec each):")
    print(f"   Current: ~{current_concurrency * 20}-{current_concurrency * 120}")
    
    print("📊 Large Bulk Uploads (10K rows, 300+ sec each):")
    print(f"   Current: ~{current_concurrency * 6}-{current_concurrency * 12}")
    
    print("\n" + "=" * 50)
    print("SCALING RECOMMENDATIONS")
    print("=" * 50)
    
    if current_concurrency == 1:
        print("⚠️  CURRENT LIMITATION: Only 1 task at a time")
        print("📈 IMMEDIATE BENEFIT: Upgrade to 2-4 concurrent tasks")
        print("🎯 RECOMMENDATION: Enable proper concurrency for production")
    else:
        print("✅ Good concurrency for single worker")
        print("📈 NEXT STEP: Consider 2 workers for queue separation")
    
    print("\n🔧 NEXT ACTIONS:")
    if current_concurrency == 1:
        print("1. Remove macOS solo pool limitation for production")
        print("2. Set concurrency to 4 for Railway deployment") 
        print("3. Implement queue-based task routing")
    else:
        print("1. Monitor task queue lengths and processing times")
        print("2. Consider 2 workers when processing > 100 tasks/hour")
        print("3. Separate email and bulk processing queues")

except Exception as e:
    print(f"Error analyzing configuration: {e}")
    import traceback
    traceback.print_exc()
