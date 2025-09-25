#!/bin/bash

# Railway startup script
# Ensures PORT variable is properly handled

# Railway automatically sets PORT, but let's ensure it exists
export PORT=${PORT:-8000}

echo "Starting FastAPI app on port $PORT..."

# Start the uvicorn server
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1
