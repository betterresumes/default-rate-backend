#!/bin/bash

# Railway startup script - runs both web app and Celery worker
# This ensures both the FastAPI server and background worker are running

echo "🚀 Starting Default Rate API with Celery Worker..."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start Celery worker in background
echo "Starting Celery worker..."
celery -A src.celery_app worker \
    --loglevel=info \
    --concurrency=1 \
    --queues=bulk_predictions \
    --hostname=worker@%h \
    --max-tasks-per-child=50 \
    --time-limit=1800 \
    --soft-time-limit=1500 &

# Give worker a moment to start
sleep 3

# Start FastAPI application
echo "Starting FastAPI server..."
exec python3 -m src.app
