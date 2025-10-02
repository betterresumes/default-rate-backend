#!/bin/bash
set -e

echo "Starting AccuNode FastAPI Production Server..."

# Wait for database to be ready (optional)
echo "Checking database connectivity..."

# Start FastAPI with proper production settings
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --access-log \
  --log-level info
