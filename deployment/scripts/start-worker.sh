#!/bin/bash

# Celery Worker Startup Script 
# This is optional - only needed for background jobs

echo "🔄 Starting Celery Worker for Background Jobs..."

# Change to backend directory to fix import paths
cd "$(dirname "$0")/../.."

# Set environment variables
export PYTHONPATH="$(pwd):${PYTHONPATH}"

# Start Celery worker with production settings
exec celery -A app.workers.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=bulk_predictions \
    --hostname=worker@%h \
    --max-tasks-per-child=100 \
    --time-limit=1800 \
    --soft-time-limit=1500 \
    --without-gossip \
    --without-mingle
