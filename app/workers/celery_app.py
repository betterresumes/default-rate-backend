import os
import sys
from celery import Celery
from dotenv import load_dotenv

# Load environment variables from .env file
# Try loading from current directory and parent directories
load_dotenv()  # Default behavior
load_dotenv('.env.local')  # Local overrides

# Also try loading from the project root explicitly
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
env_file = os.path.join(project_root, '.env')
if os.path.exists(env_file):
    load_dotenv(env_file)
    
# Debug: Print environment loading status
print(f"🔄 Celery using Redis URL: {os.getenv('REDIS_URL', 'NOT FOUND')[:20]}...{os.getenv('REDIS_URL', '')}")

# Test database URL availability
db_url = os.getenv('DATABASE_URL')
if db_url:
    # Clean the database URL
    db_url_clean = db_url.strip().strip('"').strip("'")
    print(f"✅ Database URL loaded: {db_url_clean[:20]}...{db_url_clean[-20:]}")
else:
    print("❌ DATABASE_URL not found in environment!")

if sys.platform == "darwin":  
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)

REDIS_URL = os.getenv("REDIS_URL")

if not REDIS_URL:
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = os.getenv("REDIS_PORT", "6379")
    REDIS_DB = os.getenv("REDIS_DB", "0")
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    REDIS_USER = os.getenv("REDIS_USER", os.getenv("REDISUSER", "default"))
    
    if REDIS_PASSWORD:
        if REDIS_USER and REDIS_USER != "default":
            REDIS_URL = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
        else:
            REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# Set Celery URLs (AWS compatible)
os.environ['CELERY_BROKER_URL'] = REDIS_URL
os.environ['CELERY_RESULT_BACKEND'] = REDIS_URL

print(f"🔄 Celery using Redis URL: {REDIS_URL[:20]}...{REDIS_URL[-10:] if len(REDIS_URL) > 30 else REDIS_URL}")

BROKER_URL = REDIS_URL
BACKEND_URL = REDIS_URL

celery_app = Celery(
    "bulk_prediction_worker",
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=["app.workers.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=7200,  # Increased to 2 hours for better auto-scaling
    task_track_started=True,
    
    # AUTO-SCALING OPTIMIZED SETTINGS
    task_time_limit=10 * 60,  # Reduced to 10 minutes per task for faster scaling
    task_soft_time_limit=8 * 60,  # 8 minute soft limit
    worker_prefetch_multiplier=2,  # Workers can prefetch 2 tasks for efficiency
    task_acks_late=True,
    worker_disable_rate_limits=False,
    
    # PRIORITY QUEUE SYSTEM FOR AUTO-SCALING
    task_default_queue="medium_priority",
    task_default_routing_key="medium_priority",
    
    result_accept_content=["json"],
    
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_transport_options={
        "retry_on_timeout": True,
        "connection_pool_kwargs": {
            "retry_on_timeout": True,
            "socket_timeout": 30,
            "socket_connect_timeout": 30,
        }
    },
    result_backend_transport_options={
        "retry_on_timeout": True,
        "connection_pool_kwargs": {
            "retry_on_timeout": True,
            "socket_timeout": 30,
            "socket_connect_timeout": 30,
        }
    },
    
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    result_persistent=True,
    
    worker_pool="solo" if sys.platform == "darwin" else "prefork",
    # AUTO-SCALING WORKER CONFIGURATION
    worker_concurrency=1 if sys.platform == "darwin" else 8,  # Increased from 4 to 8 workers per instance
    
    worker_max_tasks_per_child=50,  # Restart workers more frequently for stability
    
    # PRIORITY QUEUE ROUTING FOR AUTO-SCALING
    task_routes={
        # HIGH PRIORITY - Small files (< 2000 rows) - Process immediately  
        "app.workers.tasks.process_small_bulk_task": {"queue": "high_priority", "routing_key": "high_priority"},
        "app.workers.tasks.process_chunk_task": {"queue": "high_priority", "routing_key": "high_priority"},
        
        # MEDIUM PRIORITY - Normal bulk uploads
        "app.workers.tasks.process_bulk_excel_task": {"queue": "medium_priority", "routing_key": "medium_priority"},
        "app.workers.tasks.process_annual_bulk_upload_task": {"queue": "medium_priority", "routing_key": "medium_priority"},
        "app.workers.tasks.process_quarterly_bulk_upload_task": {"queue": "medium_priority", "routing_key": "medium_priority"},
        "app.workers.tasks.process_bulk_normalized_task": {"queue": "medium_priority", "routing_key": "medium_priority"},
        "app.workers.tasks.process_quarterly_bulk_task": {"queue": "medium_priority", "routing_key": "medium_priority"},
        
        # LOW PRIORITY - Large files (> 8000 rows) - Background processing
        "app.workers.tasks.process_large_bulk_task": {"queue": "low_priority", "routing_key": "low_priority"},
    },
    
    # AUTO-SCALING QUEUE DECLARATIONS
    task_create_missing_queues=True,
    task_queue_max_priority=10,
)

celery_app.conf.beat_schedule = {}

def test_redis_connection():
    """Test Redis connection and provide helpful error messages"""
    try:
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=3)
        print("✅ Redis connection successful!")
        return True
    except Exception as e:
        print(f"❌ Redis connection failed: {str(e)}")
        print(f"🔍 Using Redis URL: {REDIS_URL[:25]}...")
        print("💡 Check your Redis configuration:")
        print(f"   - REDIS_URL: {os.getenv('REDIS_URL', 'Not set')[:30]}...")
        print(f"   - REDIS_HOST: {os.getenv('REDIS_HOST', 'Not set')}")
        print(f"   - REDIS_PORT: {os.getenv('REDIS_PORT', 'Not set')}")
        print(f"   - REDIS_PASSWORD: {'Set' if os.getenv('REDIS_PASSWORD') else 'Not set'}")
        return False

if __name__ != "__main__" and os.getenv("CELERY_STARTUP_TEST", "true").lower() == "true":
    test_redis_connection()
