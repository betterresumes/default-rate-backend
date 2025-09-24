import os
import sys
from celery import Celery
from dotenv import load_dotenv

load_dotenv()
load_dotenv('.env.local')

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

if REDIS_URL and 'railway.internal' in REDIS_URL:
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
    result_expires=3600, 
    task_track_started=True,
    task_time_limit=30 * 60,  
    task_soft_time_limit=25 * 60,  
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_disable_rate_limits=False,
    task_default_queue="bulk_predictions",
    
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
    worker_concurrency=1 if sys.platform == "darwin" else 4,  
    
    worker_max_tasks_per_child=100,  
    
    task_routes={
        "app.workers.tasks.process_bulk_excel_task": {"queue": "bulk_predictions"},
        "app.workers.tasks.process_annual_bulk_upload_task": {"queue": "bulk_predictions"},
        "app.workers.tasks.process_quarterly_bulk_upload_task": {"queue": "bulk_predictions"},
        "app.workers.tasks.process_bulk_normalized_task": {"queue": "bulk_predictions"},
        "app.workers.tasks.process_quarterly_bulk_task": {"queue": "bulk_predictions"},
    }
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
