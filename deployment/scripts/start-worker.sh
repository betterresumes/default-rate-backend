#!/bin/bash

# Celery Worker Startup Script 
# This is required for robust background job processing

echo "🔄 Starting Celery Worker for Background Jobs..."

# Change to backend directory to fix import paths
cd "$(dirname "$0")/../.."

# Set environment variables
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# Start Celery worker with macOS-compatible settings
exec celery -A app.workers.celery_app worker \
    --loglevel=info \
    --pool=solo \
    --concurrency=1 \
    --queues=bulk_predictions,emails \
    --hostname=worker@%h \
    --max-tasks-per-child=100 \
    --time-limit=1800 \
    --soft-time-limit=1500 \
    --without-gossip \
    --without-mingle
