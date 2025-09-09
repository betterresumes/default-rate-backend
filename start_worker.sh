#!/bin/bash

# Start Celery Worker for Background Jobs
# This script starts the Celery worker that processes background jobs

echo "🚀 Starting Celery Worker for Bulk Predictions..."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start Celery worker
celery -A src.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=bulk_predictions \
    --hostname=worker@%h \
    --max-tasks-per-child=50 \
    --time-limit=1800 \
    --soft-time-limit=1500

echo "🛑 Celery Worker stopped"
