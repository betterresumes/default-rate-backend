#!/bin/bash

# Celery Worker Startup Script for Railway
# This will be used for the background worker service

echo "🔄 Starting Celery Worker for Background Jobs..."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start Celery worker with production settings
exec celery -A src.celery_app worker \
    --loglevel=info \
    --concurrency=2 \
    --queues=bulk_predictions \
    --hostname=worker@%h \
    --max-tasks-per-child=100 \
    --time-limit=1800 \
    --soft-time-limit=1500 \
    --without-gossip \
    --without-mingle
