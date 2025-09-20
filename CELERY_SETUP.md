# Celery Worker Setup Guide

## Overview

Your FastAPI application now supports robust bulk upload processing using **Celery workers** instead of basic FastAPI BackgroundTasks. This provides:

- ✅ **Separate worker processes** (doesn't block your API server)
- ✅ **Persistent task queue** (survives server restarts)
- ✅ **Distributed processing** (can run on multiple machines)
- ✅ **Better monitoring** and error handling
- ✅ **Scalable** (add more workers as needed)

## Architecture

```
FastAPI Server  →  Redis Queue  →  Celery Workers  →  Database
     ↑                                    ↓
   REST API                         Process Excel Files
```

## Prerequisites

1. **Redis Server** (as message broker)
2. **Updated Database** (with celery_task_id field)

## Setup Steps

### 1. Install Redis (if not already installed)

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis

# Docker (alternative)
docker run -d -p 6379:6379 redis:alpine
```

### 2. Verify Redis is Running

```bash
redis-cli ping
# Should return: PONG
```

### 3. Environment Variables

Ensure your `.env` file includes:

```env
# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
```

### 4. Start Celery Worker

```bash
# Make the script executable
chmod +x deployment/scripts/start-worker.sh

# Start the worker
./deployment/scripts/start-worker.sh
```

You should see output like:
```
🔄 Starting Celery Worker for Background Jobs...
[2025-09-20 10:30:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-09-20 10:30:00,000: INFO/MainProcess] mingle: searching for neighbor nodes...
[2025-09-20 10:30:00,000: INFO/MainProcess] mingle: all done
[2025-09-20 10:30:00,000: INFO/MainProcess] celery@worker ready.
```

### 5. Start Your FastAPI Server

```bash
# In a separate terminal
python main.py
```

## Testing the Setup

### 1. Test Bulk Upload

```bash
# Get authentication token
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "credit.admin@fintech-solutions.com",
    "password": "CreditAdmin123!"
  }' | jq -r '.access_token')

# Upload Excel file
curl -X POST "http://localhost:8000/api/v1/predictions/annual/bulk-upload-async" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@annual_predictions_5_stocks.xlsx"
```

Expected response:
```json
{
  "success": true,
  "message": "Bulk upload job started successfully using Celery workers",
  "job_id": "12345678-1234-1234-1234-123456789012",
  "task_id": "celery-task-id-12345",
  "total_rows": 5,
  "estimated_time_minutes": 1
}
```

### 2. Check Job Status

```bash
curl -X GET "http://localhost:8000/api/v1/predictions/jobs/{job_id}/status" \
  -H "Authorization: Bearer $TOKEN"
```

Expected response:
```json
{
  "success": true,
  "job": {
    "id": "12345678-1234-1234-1234-123456789012",
    "status": "completed",
    "job_type": "annual",
    "total_rows": 5,
    "processed_rows": 5,
    "successful_rows": 5,
    "failed_rows": 0,
    "progress_percentage": 100.0,
    "celery_task_id": "celery-task-id-12345",
    "celery_status": "SUCCESS",
    "celery_meta": {
      "status": "completed",
      "total_rows": 5,
      "successful_rows": 5
    }
  }
}
```

## Monitoring

### 1. Check Celery Task Status

```bash
# In Python console
from app.workers.celery_app import celery_app
result = celery_app.AsyncResult('task-id-here')
print(f"Status: {result.status}")
print(f"Result: {result.result}")
```

### 2. Monitor Redis Queue

```bash
redis-cli
> LLEN bulk_predictions  # Check queue length
> KEYS celery-*         # List all Celery keys
```

### 3. Worker Logs

The worker will show real-time logs:
```
[2025-09-20 10:35:00,000: INFO/MainProcess] Received task: app.workers.tasks.process_annual_bulk_upload_task
[2025-09-20 10:35:00,000: INFO/ForkPoolWorker-1] Task app.workers.tasks.process_annual_bulk_upload_task succeeded
```

## Production Deployment

### 1. Multiple Workers

```bash
# Start multiple workers for better performance
./deployment/scripts/start-worker.sh &  # Worker 1
./deployment/scripts/start-worker.sh &  # Worker 2
./deployment/scripts/start-worker.sh &  # Worker 3
```

### 2. Process Manager (Supervisor)

Create `/etc/supervisor/conf.d/celery-worker.conf`:
```ini
[program:celery-worker]
command=/path/to/your/project/deployment/scripts/start-worker.sh
directory=/path/to/your/project
user=www-data
numprocs=2
autostart=true
autorestart=true
startsecs=10
stopwaitsecs=600
killasgroup=true
priority=998
```

### 3. Monitoring with Flower

```bash
pip install flower
celery -A app.workers.celery_app flower --port=5555
```

Access monitoring at: http://localhost:5555

## Troubleshooting

### Issue: Redis Connection Error
```
[ERROR/MainProcess] consumer: Cannot connect to redis://localhost:6379/0
```

**Solution**: Ensure Redis is running:
```bash
redis-cli ping
# If fails, start Redis:
brew services start redis  # macOS
sudo systemctl start redis  # Linux
```

### Issue: Import Errors
```
[ERROR] Unable to import 'app.workers.tasks'
```

**Solution**: Check PYTHONPATH and ensure you're in the correct directory:
```bash
export PYTHONPATH="$(pwd):${PYTHONPATH}"
```

### Issue: Database Connection Error

**Solution**: Ensure DATABASE_URL is set in your environment:
```bash
echo $DATABASE_URL
# Should show your database connection string
```

## Benefits Over FastAPI BackgroundTasks

1. **Reliability**: Tasks survive server restarts
2. **Scalability**: Add more workers as needed
3. **Monitoring**: Better visibility into task status
4. **Error Handling**: Robust retry mechanisms
5. **Performance**: Doesn't block API server threads

## Task Types Supported

- `process_annual_bulk_upload_task`: Annual predictions from Excel/CSV
- `process_quarterly_bulk_upload_task`: Quarterly predictions from Excel/CSV
- `send_verification_email_task`: Email verification (when configured)
- `send_password_reset_email_task`: Password reset emails (when configured)

Your system is now ready for production-grade bulk processing! 🚀
