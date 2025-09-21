#!/bin/bash

# Start script for Render deployment
echo "🚀 Starting Default Rate Prediction API on Render..."

# Set default values if not provided
export HOST=${HOST:-"0.0.0.0"}
export PORT=${PORT:-8000}
export UVICORN_WORKERS=${UVICORN_WORKERS:-4}

# Check if database is available
echo "🔍 Checking database connection..."
python -c "
import os
import sys
from sqlalchemy import create_engine

try:
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        print('❌ DATABASE_URL not found')
        sys.exit(1)
    
    engine = create_engine(DATABASE_URL)
    connection = engine.connect()
    connection.close()
    print('✅ Database connection successful')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    sys.exit(1)
"

# Check if Redis is available
echo "🔍 Checking Redis connection..."
python -c "
import os
import sys
import redis

try:
    REDIS_URL = os.getenv('REDIS_URL')
    if not REDIS_URL:
        print('❌ REDIS_URL not found')
        sys.exit(1)
    
    r = redis.from_url(REDIS_URL)
    r.ping()
    print('✅ Redis connection successful')
except Exception as e:
    print(f'❌ Redis connection failed: {e}')
    sys.exit(1)
"

# Initialize database tables if needed
echo "🗃️ Initializing database tables..."
python -c "
from app.core.database import create_tables
create_tables()
print('✅ Database tables initialized')
"

# Start the application
echo "🌐 Starting FastAPI server..."
echo "📡 Server will be available at: http://${HOST}:${PORT}"
echo "📚 API documentation: http://${HOST}:${PORT}/docs"

exec uvicorn app.main:app \
    --host $HOST \
    --port $PORT \
    --workers $UVICORN_WORKERS \
    --loop uvloop \
    --http httptools \
    --access-log \
    --log-level info
