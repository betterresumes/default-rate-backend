#!/bin/bash
# macOS-specific Celery worker startup script
# Fixes SIGABRT crashes on macOS

echo "🍎 Starting Celery worker for macOS..."

# Set environment variables for macOS fork safety
export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
export PYTHONPATH="$PWD:$PYTHONPATH"

# Kill any existing celery processes
echo "🧹 Cleaning up existing workers..."
pkill -f "celery worker" 2>/dev/null || true

# Wait a moment for cleanup
sleep 2

echo "🚀 Starting Celery worker with macOS optimizations..."

# Start Celery worker with macOS-friendly settings
celery -A app.workers.celery_app worker \
    --loglevel=info \
    --pool=solo \
    --concurrency=1 \
    --queues=bulk_predictions \
    --hostname=macos-worker@%h

echo "✅ Celery worker started for macOS!"
