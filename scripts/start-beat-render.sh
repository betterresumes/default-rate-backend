#!/bin/bash

# Celery Beat start script for Render
echo "📅 Starting Celery Beat scheduler on Render..."

# Check Redis connection
echo "🔍 Checking Redis connection for Celery Beat..."
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
    print('✅ Redis connection successful for Celery Beat')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    sys.exit(1)
"

# Start Celery beat
echo "⏰ Starting Celery beat scheduler..."

exec celery -A app.workers.celery_app beat \
    --loglevel=info \
    --pidfile=/tmp/celerybeat.pid \
    --schedule=/tmp/celerybeat-schedule
