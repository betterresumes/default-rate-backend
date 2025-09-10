#!/bin/bash

# Local Celery Worker Startup Script
echo "🔄 Starting Celery Worker for Local Development..."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Load local environment variables
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
fi

echo "Starting Celery worker with development settings..."

# Start Celery worker with development settings
celery -A src.celery_app worker \
    --loglevel=debug \
    --concurrency=1 \
    --queues=bulk_predictions \
    --hostname=local-worker@%h \
    --max-tasks-per-child=10 \
    --time-limit=300 \
    --soft-time-limit=250
