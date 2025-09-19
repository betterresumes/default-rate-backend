#!/bin/bash

# Annual Bulk Upload System Startup Script
# This script starts all the necessary services for the annual prediction system

set -e

echo "🚀 Starting Annual Bulk Upload System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please create one first:"
    echo "   python3 -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check required environment variables
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if Redis is running
echo "🔍 Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis is not running. Please start Redis:"
    echo "   brew services start redis  # On macOS"
    echo "   sudo systemctl start redis  # On Linux"
    exit 1
fi

# Check if PostgreSQL is running
echo "🔍 Checking PostgreSQL connection..."
if ! python3 -c "
import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()
try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    conn.close()
    print('✅ PostgreSQL connected')
except Exception as e:
    print(f'❌ PostgreSQL connection failed: {e}')
    exit(1)
" 2>/dev/null; then
    echo "❌ PostgreSQL connection failed. Please check your DATABASE_URL in .env"
    exit 1
fi

echo "✅ All dependencies are ready!"
echo ""
echo "🎯 Starting services..."
echo ""

# Function to handle cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Shutting down services..."
    kill $(jobs -p) 2>/dev/null || true
    wait
    echo "✅ All services stopped"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Start FastAPI server
echo "🌐 Starting FastAPI server on http://localhost:8000..."
uvicorn src.app:app --host 0.0.0.0 --port 8000 --reload &
SERVER_PID=$!

# Wait a bit for server to start
sleep 3

# Start Celery worker
echo "⚙️  Starting Celery worker for bulk predictions..."
python3 -m celery -A src.celery_app worker --loglevel=info --queues=bulk_predictions --pool=prefork --concurrency=1 &
WORKER_PID=$!

# Wait a bit for worker to start
sleep 3

echo ""
echo "🎉 Annual Bulk Upload System is now running!"
echo ""
echo "📊 Available Services:"
echo "   • API Server: http://localhost:8000"
echo "   • API Docs: http://localhost:8000/docs"
echo "   • Health Check: http://localhost:8000/health"
echo ""
echo "📁 Upload Endpoints:"
echo "   • Bulk Upload: POST /api/predictions/bulk-predict-async"
echo "   • Job Status: GET /api/predictions/job-status/{job_id}"
echo ""
echo "🔧 Test Files Available:"
echo "   • test_mixed_quarters.xlsx (5 records with Q1,Q2,Q3,Q4)"
echo "   • test_small_50_records.xlsx (50 records with Q4)"
echo ""
echo "Press Ctrl+C to stop all services..."

# Wait for user interrupt
wait
