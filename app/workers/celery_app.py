import os
import sys
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
load_dotenv('.env.local')

# Fix for macOS fork safety issues
if sys.platform == "darwin":  # macOS
    os.environ.setdefault("OBJC_DISABLE_INITIALIZE_FORK_SAFETY", "YES")
    # Force use of spawn instead of fork on macOS
    import multiprocessing
    multiprocessing.set_start_method('spawn', force=True)

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_DB = os.getenv("REDIS_DB", "0")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")

if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

celery_app = Celery(
    "bulk_prediction_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
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
    
    # Fix for exception serialization issues
    result_accept_content=["json"],
    result_backend_transport_options={
        "master_name": "mymaster",
        "retry_on_timeout": True,
        "connection_pool_kwargs": {
            "retry_on_timeout": True,
        }
    },
    
    # Additional error handling configuration
    task_reject_on_worker_lost=True,
    task_ignore_result=False,
    result_persistent=True,
    
    # macOS specific fixes
    worker_pool="solo" if sys.platform == "darwin" else "prefork",
    worker_concurrency=1 if sys.platform == "darwin" else None,
    
    task_routes={
        "app.workers.tasks.process_bulk_excel_task": {"queue": "bulk_predictions"},
        "app.workers.tasks.process_annual_bulk_upload_task": {"queue": "bulk_predictions"},
        "app.workers.tasks.process_quarterly_bulk_upload_task": {"queue": "bulk_predictions"},
        "app.workers.tasks.send_verification_email_task": {"queue": "emails"},
        "app.workers.tasks.send_password_reset_email_task": {"queue": "emails"},
    },
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True
)

celery_app.conf.beat_schedule = {}
