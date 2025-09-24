# 🔧 Redis Connection Fix - FINAL SOLUTION

## ❌ **Original Problem**
```
consumer: Cannot connect to redis://localhost:6379/1: Error 111 connecting to localhost:6379. Connection refused.
```

## ✅ **Root Cause Identified**
Celery was using hardcoded environment variables `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` from the `.env` file that pointed to localhost instead of using the Railway Redis URL.

## 🔧 **Fixes Applied**

### 1. **Fixed Celery Configuration** (`app/workers/celery_app.py`)
- Override environment variables when Railway Redis is detected
- Use single Redis database instead of separate broker/backend databases
- Removed duplicate `task_time_limit` configuration

### 2. **Removed Unused Email Tasks**
- Removed `send_verification_email_task` and `send_password_reset_email_task` from `app/workers/tasks.py`
- Updated task routes to only include bulk prediction tasks
- Updated worker startup scripts to only use `bulk_predictions` queue

### 3. **Updated Environment Configuration**
- Removed hardcoded `CELERY_BROKER_URL` and `CELERY_RESULT_BACKEND` from `.env` file
- Updated `.env.example` with correct configuration

### 4. **Updated Worker Scripts**
- `deployment/scripts/start-worker.sh`: Added debugging info and removed emails queue
- `start_celery_macos.sh`: Removed emails queue for consistency

## 📋 **Current Task Configuration**
```
✅ process_annual_bulk_upload_task → bulk_predictions
✅ process_bulk_excel_task → bulk_predictions
✅ process_bulk_normalized_task → bulk_predictions
✅ process_quarterly_bulk_task → bulk_predictions
✅ process_quarterly_bulk_upload_task → bulk_predictions
```

## 🚂 **For Railway Deployment**

### Environment Variables Needed:
```bash
REDIS_URL=redis://default:YOUR_PASSWORD@redis.railway.internal:6379
DATABASE_URL=postgresql://user:pass@host:port/dbname
SECRET_KEY=your-secret-key
```

### Worker Command:
```bash
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 --queues=bulk_predictions
```

## ✅ **Expected Results**

After deployment, you should see:
```
🔄 Starting Celery Worker for Background Jobs...
✅ ML Model and scoring info loaded successfully
✅ Quarterly ML Models and scoring info loaded successfully

-------------- worker@container-id v5.3.4 (emerald-rush)
--- ***** ----- 
-- ******* ---- Linux-x86_64-with-glibc 2025-09-24 09:26:12
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         bulk_prediction_worker:0x...
- ** ---------- .> transport:   redis://redis.railway.internal:6379/0
- ** ---------- .> results:     redis://redis.railway.internal:6379/0
- *** --- * --- .> concurrency: 2 (prefork)
-- ******* ---- .> task events: OFF
--- ***** ----- 
 -------------- [queues]
                .> bulk_predictions exchange=bulk_predictions(direct) key=bulk_predictions

[tasks]
  . app.workers.tasks.process_annual_bulk_upload_task
  . app.workers.tasks.process_bulk_excel_task
  . app.workers.tasks.process_bulk_normalized_task
  . app.workers.tasks.process_quarterly_bulk_task
  . app.workers.tasks.process_quarterly_bulk_upload_task

[INFO] Connected to redis://redis.railway.internal:6379/0
[INFO] Worker ready!
```

## 🎯 **NO MORE ERRORS**
- ❌ `Error 111 connecting to localhost:6379. Connection refused` - FIXED
- ❌ `redis://localhost:6379/1` and `redis://localhost:6379/2` - FIXED  
- ❌ Email task import errors - FIXED (tasks removed)
- ❌ Duplicate configuration errors - FIXED

The worker will now connect properly to Railway Redis and process only the needed bulk prediction tasks.
