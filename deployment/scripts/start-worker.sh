#!/bin/bash

# Simplified Railway Celery Worker Startup Script
# Based on the working local command: python3 -m celery -A app.workers.celery_app worker --loglevel=info --concurrency=4 --queues=high_priority,medium_priority,low_priority

set -e

echo "🚀 Starting Railway Celery Worker..."
echo "📅 Started at: $(date)"
echo "🏗️ Environment: ${RAILWAY_ENVIRONMENT:-production}"
echo "🔧 Service: ${RAILWAY_SERVICE_NAME:-workers}"

# Environment variables with Railway-optimized defaults
export WORKER_CONCURRENCY="${CELERY_WORKER_CONCURRENCY:-8}"
export MAX_TASKS_PER_CHILD="${CELERY_MAX_TASKS_PER_CHILD:-50}"
export TASK_TIMEOUT="${CELERY_TASK_TIMEOUT:-600}"
export SOFT_TIMEOUT="${CELERY_SOFT_TIMEOUT:-480}"

# Railway-specific optimizations
export CELERY_OPTIMIZATION="railway"
export PYTHONPATH="${PYTHONPATH}:."

echo "📊 Worker Configuration:"
echo "   - Concurrency: $WORKER_CONCURRENCY"
echo "   - Max tasks per child: $MAX_TASKS_PER_CHILD"
echo "   - Task timeout: $TASK_TIMEOUT seconds"
echo "   - Queues: high_priority, medium_priority, low_priority"

# Graceful shutdown handler
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

# Start the worker using the exact format that works locally
echo "🎯 Starting Celery worker..."
python3 -m celery -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=$WORKER_CONCURRENCY \
    --queues=high_priority,medium_priority,low_priority \
    --max-tasks-per-child=$MAX_TASKS_PER_CHILD \
    --time-limit=$TASK_TIMEOUT \
    --soft-time-limit=$SOFT_TIMEOUT \
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
