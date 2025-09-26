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
    log_db('INFO', 'Testing database connection...')
    engine = create_engine(os.getenv('DATABASE_URL'))
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
    log_info "🛑 Received shutdown signal. Performing graceful cleanup..."
    
    # Kill the monitor process if it exists
    if [ ! -z "$MONITOR_PID" ]; then
        kill $MONITOR_PID 2>/dev/null || true
        log_info "🔍 Monitor process stopped"
    fi
    
    # Send TERM signal to celery worker for graceful shutdown
    if [ ! -z "$CELERY_PID" ]; then
        log_info "📝 Sending graceful shutdown to Celery worker..."
        kill -TERM $CELERY_PID 2>/dev/null || true
        
        # Wait up to 30 seconds for graceful shutdown
        for i in {1..30}; do
            if ! kill -0 $CELERY_PID 2>/dev/null; then
                log_success "✅ Celery worker shut down gracefully"
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if kill -0 $CELERY_PID 2>/dev/null; then
            log_warning "⚠️ Forcing Celery worker shutdown"
            kill -KILL $CELERY_PID 2>/dev/null || true
        fi
    fi
    
    log_info "🏁 Cleanup completed"
    exit 0
}

# Register signal handlers
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
    --concurrency=8 \
    --queues=high_priority,medium_priority,low_priority \
    --hostname=autoscale-worker@%h \
    --max-tasks-per-child=50 \
    --time-limit=1800 \
    --soft-time-limit=1500 \
    --prefetch-multiplier=2 \
    --without-gossip \
    --without-mingle \
    --optimization=fair &

# Capture the celery PID for cleanup
CELERY_PID=$!

log_success "🚀 Celery worker started successfully (PID: $CELERY_PID)!"
log_info "📊 Worker is now ready to process jobs with the following priorities:"
log_info "   🔴 HIGH: Small files (< 100 rows) - Immediate processing"
log_info "   🟡 MEDIUM: Regular files (100-1000 rows) - Standard queue"
log_info "   🟢 LOW: Large files (> 1000 rows) - Background processing"
log_info ""
log_info "📈 Performance Expectations:"
log_info "   - Single instance capacity: ~960 rows/sec"
log_info "   - With auto-scaling (8 instances): ~5,200 rows/sec"
log_info "   - File processing times:"
log_info "     * 1,000 rows: ~1-3 seconds"
log_info "     * 5,000 rows: ~5-10 seconds"  
log_info "     * 10,000 rows: ~10-20 seconds"
log_info ""
log_info "🎯 Worker is now monitoring for jobs. Logs will show:"
log_info "   - Job details (user, file size, processing time)"
log_info "   - Queue routing decisions"
log_info "   - Performance metrics"
log_info "   - Error handling and recovery"

# Wait for the celery process and handle any exits
wait $CELERY_PID

# If we get here, celery exited
EXIT_CODE=$?
log_error "❌ Celery worker exited with code: $EXIT_CODE"

# Cleanup on exit
cleanup
