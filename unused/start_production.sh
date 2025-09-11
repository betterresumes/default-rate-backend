# Optimized startup script for production deployment
#!/bin/bash

# Production startup script that minimizes cold start time
# Use this for VPS deployments

set -e

echo "🚀 Starting FastAPI Production Server..."

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Pre-load ML models to avoid cold start delays
echo "🤖 Pre-loading ML models..."
python -c "
import sys
sys.path.append('src')
from ml_service import ml_service
print('✅ ML models loaded successfully')
"

# Create database tables
echo "🗄️ Initializing database..."
python -c "
import sys
sys.path.append('src')
from database import create_tables
create_tables()
print('✅ Database initialized')
"

# Start server with optimized settings
echo "🌟 Starting Uvicorn server..."
exec uvicorn src.app:app \
    --host 0.0.0.0 \
    --port ${PORT:-8000} \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --log-level info
