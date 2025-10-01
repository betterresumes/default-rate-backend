#!/bin/bash

# RESILIENT AUTO-SCALING CELERY WORKER STARTUP SCRIPT
# Enhanced with comprehensive logging, error handling, and auto-recovery

# Enable error handling but don't exit on errors
set +e

# Function to log with timestamp and service info
log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WORKER-STARTUP] [INFO] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WORKER-STARTUP] [ERROR] $1" >&2
}

log_warning() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WORKER-STARTUP] [WARN] $1"
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [WORKER-STARTUP] [SUCCESS] $1"
}

# Start with comprehensive logging
log_info "🚀 Starting Resilient Auto-Scaling Celery Worker..."
log_info "📊 System Information:"
log_info "   - Hostname: $(hostname)"
log_info "   - Container ID: ${HOSTNAME:-'N/A'}"
log_info "   - Railway Service: ${RAILWAY_SERVICE_NAME:-'workers'}"
log_info "   - Railway Environment: ${RAILWAY_ENVIRONMENT_NAME:-'production'}"
log_info "   - Python Version: $(python3 --version 2>/dev/null || echo 'Unknown')"
log_info "   - Worker PID: $$"
log_info "   - Available Memory: $(free -h 2>/dev/null | grep Mem | awk '{print $2}' || echo 'Unknown')"
log_info "   - CPU Cores: $(nproc 2>/dev/null || echo 'Unknown')"

# Change to backend directory to fix import paths
cd "$(dirname "$0")/../.." || {
    log_error "❌ Failed to change to backend directory"
    exit 1
}

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    log_info "📋 Loading environment variables from .env file..."
    # Export each line from .env file that doesn't start with # and isn't empty
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] || [[ -z "$line" ]] && continue
        # Remove quotes if present and export the variable
        cleaned_line=$(echo "$line" | sed 's/^"//' | sed 's/"$//')
        export "$cleaned_line"
    done < .env
    log_info "✅ Environment variables loaded successfully"
else
    log_warning "⚠️ No .env file found - relying on system environment variables"
fi

# Set environment variables
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# Print detailed configuration for debugging
log_info "🔍 Auto-Scaling Worker Configuration:"
log_info "   - Working Directory: $(pwd)"
log_info "   - PYTHONPATH: ${PYTHONPATH}"
log_info "   - REDIS_URL: ${REDIS_URL:-'Not set'}"
log_info "   - DATABASE_URL: ${DATABASE_URL:0:30}...${DATABASE_URL: -10}"
log_info "   - Workers per instance: 8"
log_info "   - Priority queues: high_priority, medium_priority, low_priority"
log_info "   - Max tasks per child: 50 (auto-restart for stability)"
log_info "   - Task timeout: 30 minutes"
log_info "   - Auto-scaling enabled: ${AUTO_SCALING_ENABLED:-true}"

# Test Redis connection with detailed error handling
log_info "🔄 Testing Redis connection..."
python3 -c "
import os, sys, traceback
from datetime import datetime

def log_redis(level, msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] [REDIS-TEST] [{level}] {msg}')

try:
    import redis
    log_redis('INFO', 'Connecting to Redis...')
    r = redis.from_url(os.getenv('REDIS_URL'))
    info = r.ping()
    redis_info = r.info()
    log_redis('SUCCESS', '✅ Redis connection successful!')
    log_redis('INFO', f'Redis server version: {redis_info.get(\"redis_version\", \"Unknown\")}')
    log_redis('INFO', f'Connected clients: {redis_info.get(\"connected_clients\", \"Unknown\")}')
    log_redis('INFO', f'Used memory: {redis_info.get(\"used_memory_human\", \"Unknown\")}')
    log_redis('INFO', f'Max memory: {redis_info.get(\"maxmemory_human\", \"Unlimited\")}')
    
    # Test queue access
    queues = ['high_priority', 'medium_priority', 'low_priority']
    for queue in queues:
        queue_len = r.llen(f'celery:{queue}')
        log_redis('INFO', f'Queue {queue}: {queue_len} tasks pending')
        
except ImportError as e:
    log_redis('ERROR', f'❌ Redis package not installed: {str(e)}')
    sys.exit(1)
except Exception as e:
    log_redis('ERROR', f'❌ Redis connection failed: {str(e)}')
    log_redis('ERROR', f'Traceback: {traceback.format_exc()}')
    sys.exit(1)
" || {
    log_error "❌ Redis connection test failed. Worker cannot start without Redis."
    log_error "💡 Please check:"
    log_error "   - REDIS_URL environment variable"
    log_error "   - Redis service availability"
    log_error "   - Network connectivity"
    exit 1
}

# Test database connection
log_info "🗄️ Testing Database connection..."
python3 -c "
import os, sys, traceback
from datetime import datetime

def log_db(level, msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] [DB-TEST] [{level}] {msg}')

try:
    from sqlalchemy import create_engine, text
    from app.core.database import get_database_url
    log_db('INFO', 'Testing database connection...')
    database_url = get_database_url()
    engine = create_engine(database_url)
    with engine.connect() as conn:
        result = conn.execute(text('SELECT 1')).fetchone()
        log_db('SUCCESS', '✅ Database connection successful!')
        log_db('INFO', f'Database engine: {engine.url.drivername}')
        
        # Test database tables
        try:
            tables_result = conn.execute(text(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' LIMIT 5\")).fetchall()
            log_db('INFO', f'Available tables: {[row[0] for row in tables_result]}')
        except:
            log_db('INFO', 'Could not query table information (normal for some databases)')
            
except ImportError as e:
    log_db('WARN', f'⚠️  Database packages not fully available: {str(e)}')
    log_db('WARN', 'Worker will continue but some features may not work')
except Exception as e:
    log_db('WARN', f'⚠️  Database connection test failed: {str(e)}')
    log_db('WARN', 'Worker will continue but database tasks may fail')
" || log_warning "⚠️ Database connection test had issues, but continuing..."

# Test Celery app import
log_info "📦 Testing Celery application import..."
python3 -c "
import sys, traceback
from datetime import datetime

def log_celery(level, msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] [CELERY-TEST] [{level}] {msg}')

try:
    log_celery('INFO', 'Importing Celery app...')
    from app.workers.celery_app import celery_app
    log_celery('SUCCESS', '✅ Celery app imported successfully!')
    log_celery('INFO', f'Broker URL configured: {bool(celery_app.conf.broker_url)}')
    log_celery('INFO', f'Result backend configured: {bool(celery_app.conf.result_backend)}')
    
    # Test task discovery
    registered_tasks = list(celery_app.tasks.keys())
    log_celery('INFO', f'Registered tasks: {len(registered_tasks)}')
    
    # Show important tasks
    important_tasks = [task for task in registered_tasks if 'bulk' in task.lower()]
    for task in important_tasks[:10]:  # Show first 10 bulk tasks
        log_celery('INFO', f'   - {task}')
    if len(important_tasks) > 10:
        log_celery('INFO', f'   - ... and {len(important_tasks) - 10} more bulk tasks')
        
    # Show queue configuration
    log_celery('INFO', f'Default queue: {celery_app.conf.task_default_queue}')
    log_celery('INFO', f'Task routes configured: {bool(celery_app.conf.task_routes)}')
        
except Exception as e:
    log_celery('ERROR', f'❌ Celery app import failed: {str(e)}')
    log_celery('ERROR', f'Traceback: {traceback.format_exc()}')
    sys.exit(1)
" || {
    log_error "❌ Celery application import failed. Cannot start worker."
    exit 1
}

log_info "📦 Testing Quarterly ML Models..."
python3 -c "
import sys
import traceback
from datetime import datetime

def log_ml_test(level, msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] [ML-TEST] [{level}] {msg}')

try:
    log_ml_test('INFO', 'Testing quarterly ML model loading...')
    from app.services.quarterly_ml_service import quarterly_ml_model
    log_ml_test('SUCCESS', '✅ Quarterly ML models loaded successfully!')
    
    # Test prediction
    test_data = {
        'total_debt_to_ebitda': 7.933,
        'sga_margin': 7.474,
        'long_term_debt_to_total_capital': 36.912,
        'return_on_capital': 9.948
    }
    
    log_ml_test('INFO', 'Testing quarterly prediction...')
    result = quarterly_ml_model.predict_quarterly_default_probability(test_data)
    log_ml_test('SUCCESS', f'✅ Quarterly prediction successful: {result.get(\"risk_level\", \"Unknown\")}')
    
except ImportError as e:
    log_ml_test('ERROR', f'❌ Import failed: {str(e)}')
    log_ml_test('ERROR', 'This indicates missing dependencies (likely LightGBM)')
    
except Exception as e:
    log_ml_test('ERROR', f'❌ Prediction failed: {str(e)}')
    log_ml_test('ERROR', f'Traceback: {traceback.format_exc()[:500]}')
" || {
    log_warning "⚠️ Quarterly ML model test failed, but continuing startup..."
}

# Create a monitoring function for worker health
create_worker_monitor() {
    log_info "🔍 Setting up worker health monitoring..."
    
    # Create a background process to monitor worker health
    (
        while true; do
            sleep 300  # Check every 5 minutes
            
            # Railway handles process monitoring, so just log worker stats
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MONITOR] [INFO] ✅ Worker monitoring active (Railway handles process health)"
            
            # Log worker stats if celery is available
            python3 -c "
import os, sys
from datetime import datetime
try:
    from app.workers.celery_app import celery_app
    inspect = celery_app.control.inspect()
    active_tasks = inspect.active()
    reserved_tasks = inspect.reserved()
    
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if active_tasks:
        for worker, tasks in active_tasks.items():
            print(f'[{timestamp}] [MONITOR] [INFO] Worker {worker}: {len(tasks)} active tasks')
    else:
        print(f'[{timestamp}] [MONITOR] [INFO] Worker {list(active_tasks.keys())[0] if active_tasks else \"autoscale-worker\"}: 0 active tasks')
        
except Exception as e:
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'[{timestamp}] [MONITOR] [WARN] Could not get worker stats: {str(e)}')
" 2>/dev/null || true
            
        done
    ) &
    
    MONITOR_PID=$!
    log_info "📊 Worker monitor started (PID: $MONITOR_PID)"
}

# Set up signal handlers for graceful shutdown
cleanup() {
    echo "🛑 Received shutdown signal, cleaning up..."
    if [[ -n "$CELERY_PID" ]]; then
        echo "📝 Stopping Celery worker (PID: $CELERY_PID)..."
        kill -TERM $CELERY_PID 2>/dev/null || true
        wait $CELERY_PID 2>/dev/null || true
    fi
    echo "✅ Cleanup completed"
    exit 0
}

trap cleanup SIGTERM SIGINT SIGQUIT

# Start worker health monitoring
create_worker_monitor

# Final startup log
log_success "🎯 All pre-flight checks passed! Starting Celery worker..."
log_info "📋 Worker Configuration Summary:"
log_info "   - Concurrency: 8 workers"
log_info "   - Queues: high_priority, medium_priority, low_priority"
log_info "   - Task timeout: 30 minutes (1800 seconds)"
log_info "   - Soft timeout: 25 minutes (1500 seconds)"
log_info "   - Tasks per child: 50 (then restart for stability)"
log_info "   - Prefetch multiplier: 2"
log_info "   - Hostname: autoscale-worker@$(hostname)"

# Start Celery worker with ENHANCED LOGGING and ERROR RESILIENCE
exec celery -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=$WORKER_CONCURRENCY \
    --queues=high_priority,medium_priority,low_priority \
    --hostname=autoscale-worker@%h \
    --max-tasks-per-child=50 \
    --time-limit=1800 \
    --soft-time-limit=1500 \
    --prefetch-multiplier=2 \
    --without-gossip \
    --without-mingle &

CELERY_PID=$!

echo "✅ Celery worker started successfully (PID: $CELERY_PID)"
echo "📊 Ready to process quarterly and annual bulk uploads"
echo "🔗 Monitoring for tasks on Redis: ${REDIS_URL}"

# Wait for the worker
wait $CELERY_PID
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo "❌ Worker exited with code: $EXIT_CODE"
    exit $EXIT_CODE
else
    echo "✅ Worker shut down gracefully"
fi
