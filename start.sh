#!/bin/bash

# AWS-optimized startup script for AccuNode
set -e

export PORT=${PORT:-8000}
export WORKERS=${WORKERS:-4}
export ENVIRONMENT=${ENVIRONMENT:-production}

echo "🚀 Starting AccuNode API..."
echo "🌍 Environment: $ENVIRONMENT"
echo "🔧 Port: $PORT"  
echo "👷 Workers: $WORKERS"

# Health check for dependencies
echo "🔍 Checking dependencies..."

# Wait for database if DATABASE_URL is set
if [ ! -z "$DATABASE_URL" ]; then
    echo "⏳ Waiting for database connection..."
    python -c "
import os, time, psycopg2
db_url = os.getenv('DATABASE_URL')
if db_url:
    for i in range(30):
        try:
            conn = psycopg2.connect(db_url)
            conn.close()
            print('✅ Database connected')
            break
        except Exception as e:
            print(f'⏳ Database not ready ({i+1}/30): {e}')
            time.sleep(2)
    else:
        print('❌ Database connection timeout')
        exit(1)
"
fi

# Wait for Redis if REDIS_URL is set
if [ ! -z "$REDIS_URL" ]; then
    echo "⏳ Waiting for Redis connection..."
    python -c "
import os, time, redis
redis_url = os.getenv('REDIS_URL')
if redis_url:
    for i in range(30):
        try:
            r = redis.from_url(redis_url)
            r.ping()
            print('✅ Redis connected')
            break
        except Exception as e:
            print(f'⏳ Redis not ready ({i+1}/30): {e}')
            time.sleep(2)
    else:
        print('❌ Redis connection timeout')
        exit(1)
"
fi

echo "✅ Dependencies ready, starting server..."

# Start the application with production settings
if [ "$ENVIRONMENT" = "production" ]; then
    echo "🏭 Production mode: Using Gunicorn with Uvicorn workers"
    exec gunicorn app.main:app \
        --bind 0.0.0.0:$PORT \
        --workers $WORKERS \
        --worker-class uvicorn.workers.UvicornWorker \
        --timeout 120 \
        --keepalive 5 \
        --max-requests 1000 \
        --max-requests-jitter 100 \
        --access-logfile - \
        --error-logfile - \
        --log-level warning
else
    echo "🛠️ Development mode: Using Uvicorn"
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "$PORT" \
        --workers 1 \
        --reload
fi
