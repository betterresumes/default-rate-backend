#!/bin/bash

# Celery Worker start script for Render
echo "🔄 Starting Celery Worker on Render..."

# Set default values
export CELERY_CONCURRENCY=${CELERY_CONCURRENCY:-2}
export CELERY_POOL=${CELERY_POOL:-solo}
export CELERY_LOGLEVEL=${CELERY_LOGLEVEL:-info}

# Check Redis connection
echo "🔍 Checking Redis connection for Celery..."
python -c "
import os
import sys
import redis

try:
    CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL') or os.getenv('REDIS_URL')
    if not CELERY_BROKER_URL:
        print('❌ CELERY_BROKER_URL not found')
        sys.exit(1)
    
    r = redis.from_url(CELERY_BROKER_URL)
    r.ping()
    print('✅ Redis connection successful for Celery')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    sys.exit(1)
"

# Start Celery worker
echo "🏃 Starting Celery worker..."
echo "⚙️ Concurrency: $CELERY_CONCURRENCY"
echo "🏊 Pool: $CELERY_POOL"
echo "📊 Log Level: $CELERY_LOGLEVEL"

exec celery -A app.workers.celery_app worker \
    --loglevel=$CELERY_LOGLEVEL \
    --concurrency=$CELERY_CONCURRENCY \
    --pool=$CELERY_POOL \
    --without-gossip \
    --without-mingle \
    --without-heartbeat
