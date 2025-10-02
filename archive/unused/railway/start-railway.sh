#!/bin/bash

# Railway Production Startup Script
# Runs FastAPI server for Railway deployment

echo "🚀 Starting Default Rate API for Railway..."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Use PORT from Railway environment, fallback to 8000
PORT=${PORT:-8000}

echo "Starting FastAPI server on port $PORT..."

# Start FastAPI with production settings
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 1 \
    --loop uvloop \
    --http httptools \
    --access-log \
    --no-use-colors
