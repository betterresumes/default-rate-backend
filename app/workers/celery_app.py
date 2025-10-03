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
    
# Enhanced worker startup logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("=" * 50)
logger.info("🔧 CELERY WORKER STARTUP")
logger.info("=" * 50)

# Environment check
environment = os.getenv("ENVIRONMENT", "development")
aws_region = os.getenv("AWS_REGION", "local")
logger.info(f"🌍 Environment: {environment}")
logger.info(f"🏗️ AWS Region: {aws_region}")

# Redis configuration check
redis_url = os.getenv('REDIS_URL')
if redis_url:
    # Show first and last parts for debugging without exposing credentials
    redis_display = f"{redis_url[:20]}...{redis_url[-10:]}" if len(redis_url) > 30 else redis_url
    logger.info(f"✅ Redis URL configured: {redis_display}")
else:
    logger.error("❌ REDIS_URL not found! Worker will fail to start.")
    logger.info("   Available environment variables:")
    for key in sorted(os.environ.keys()):
        if 'redis' in key.lower() or 'cache' in key.lower():
            logger.info(f"      {key}: {os.environ[key]}")

# Database URL check (for workers that need DB access)
db_url = os.getenv('DATABASE_URL')
# Also check the SSM parameter format that might be causing issues
db_url_alt = os.getenv('DATABASE_URL_ALT') or os.getenv('DB_URL')

if db_url:
    logger.info(f"✅ DATABASE_URL configured: {db_url[:20]}...{db_url[-20:]}")
elif db_url_alt:
    logger.info(f"✅ Alternative DB URL found: {db_url_alt[:20]}...{db_url_alt[-20:]}")
    os.environ['DATABASE_URL'] = db_url_alt  # Set as primary
else:
    logger.error("❌ No DATABASE_URL found!")
    logger.info("   Checked variables: DATABASE_URL, DATABASE_URL_ALT, DB_URL")
    logger.info("   Available DB-related environment variables:")
    for key in sorted(os.environ.keys()):
        if any(keyword in key.lower() for keyword in ['db', 'database', 'postgres']):
            value = os.environ[key]
            # Mask sensitive info
            if any(sensitive in key.lower() for sensitive in ['password', 'secret', 'key']):
                value = "***masked***"
            logger.info(f"      {key}: {value}")

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
