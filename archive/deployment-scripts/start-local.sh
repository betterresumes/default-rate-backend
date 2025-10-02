#!/bin/bash

# Local Development Startup Script
echo "🚀 Starting Default Rate API for Local Development..."

# Set environment variables
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
export DEBUG=True

# Load local environment variables
if [ -f .env.local ]; then
    export $(cat .env.local | grep -v '^#' | xargs)
fi

echo "Starting FastAPI server with auto-reload..."

# Start FastAPI with development settings (auto-reload enabled)
uvicorn src.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level debug
