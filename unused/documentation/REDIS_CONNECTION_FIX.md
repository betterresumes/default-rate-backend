# 🔧 Redis Connection Error Fix

## ❌ **Error Description**
```
consumer: Cannot connect to redis://localhost:6379/1: Error 111 connecting to localhost:6379. Connection refused..
```

## 🔍 **Root Cause**
Celery was trying to connect to local Redis (`localhost:6379`) instead of using the Railway Redis configuration.

## ✅ **Fix Applied**

### **1. Updated Celery Configuration**
Updated `app/workers/celery_app.py` to properly handle Railway Redis URLs:

```python
# Before (❌): Manual URL construction
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# After (✅): Use REDIS_URL first, fallback to components
REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    # Fallback to individual variables with proper user handling
    REDIS_USER = os.getenv("REDIS_USER", os.getenv("REDISUSER", "default"))
    if REDIS_USER and REDIS_USER != "default":
        REDIS_URL = f"redis://{REDIS_USER}:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
    else:
        REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
```

### **2. Enhanced Connection Configuration**
Added better connection handling for cloud deployments:

```python
broker_connection_retry_on_startup=True,
broker_connection_retry=True,
broker_connection_max_retries=10,
broker_transport_options={
    "retry_on_timeout": True,
    "connection_pool_kwargs": {
        "socket_timeout": 30,
        "socket_connect_timeout": 30,
    }
}
```

### **3. Added Connection Testing**
Added startup connection test with helpful error messages.

## 🚀 **Railway Environment Variables**

### **Set These in Railway:**
```bash
# Primary (recommended)
REDIS_URL="redis://default:WKIFhoxBMxTwUgkrPoOdmDrPfyTvfbYB@redis.railway.internal:6379"

# Or individual components (fallback)
REDIS_HOST="redis.railway.internal"
REDIS_PORT="6379"
REDIS_PASSWORD="WKIFhoxBMxTwUgkrPoOdmDrPfyTvfbYB"
REDIS_DB="0"
REDISUSER="default"
```

### **For Development:**
```bash
# Local Redis
REDIS_URL="redis://localhost:6379/0"

# Or
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_DB="0"
# No password for local
```

## 🔧 **Testing the Fix**

### **1. Test Redis Connection**
```python
# Run this in Python to test
import os
from app.workers.celery_app import celery_app

# Test connection
with celery_app.connection() as conn:
    conn.ensure_connection(max_retries=3)
print("✅ Redis connection successful!")
```

### **2. Start Celery Worker**
```bash
# Railway/Production
celery -A app.workers.celery_app worker --loglevel=info

# macOS Development
./start_celery_macos.sh
```

### **3. Test Task Execution**
```python
# Test a simple task
from app.workers.tasks import send_verification_email_task
result = send_verification_email_task.delay("test@example.com", "testuser", "123456")
print(f"Task ID: {result.id}")
print(f"Status: {result.status}")
```

## 📋 **Troubleshooting Guide**

### **Connection Refused Error**
```
Error 111 connecting to localhost:6379. Connection refused
```

**Solutions:**
1. ✅ **Check REDIS_URL** is set correctly
2. ✅ **Verify Railway Redis service** is running
3. ✅ **Check Railway internal networking** (use `.railway.internal` domain)

### **Authentication Failed**
```
NOAUTH Authentication required
```

**Solutions:**
1. ✅ **Check REDIS_PASSWORD** is set
2. ✅ **Verify password** matches Railway Redis password
3. ✅ **Check user credentials** (default user vs custom user)

### **Connection Timeout**
```
TimeoutError: Operation timed out
```

**Solutions:**
1. ✅ **Increase timeout values** (already added in fix)
2. ✅ **Check Railway network** connectivity
3. ✅ **Verify Redis service** is healthy

## 🔄 **Railway Deployment Steps**

### **1. Set Environment Variables in Railway**
```bash
# In Railway dashboard, add these variables:
REDIS_URL=redis://default:WKIFhoxBMxTwUgkrPoOdmDrPfyTvfbYB@redis.railway.internal:6379
```

### **2. Deploy Updated Code**
```bash
git add .
git commit -m "Fix Redis connection for Railway deployment"
git push origin main
```

### **3. Restart Services**
- Main API service will restart automatically
- Worker service (if separate) needs manual restart

### **4. Verify Connection**
Check logs for:
```
✅ Redis connection successful!
🔄 Starting Celery Worker for Background Jobs...
[INFO] Connected to redis://redis.railway.internal:6379/0
```

## ⚡ **Performance Optimizations**

### **Connection Pooling**
```python
broker_transport_options={
    "connection_pool_kwargs": {
        "max_connections": 20,
        "socket_timeout": 30,
    }
}
```

### **Task Routing**
```python
task_routes={
    "*.send_verification_email_task": {"queue": "emails"},
    "*.process_*_bulk_upload_task": {"queue": "bulk_predictions"},
}
```

## 📊 **Monitoring Redis Connection**

### **Health Check Endpoint**
Add to your FastAPI app:

```python
@app.get("/health/redis")
async def redis_health():
    try:
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=1)
        return {"status": "healthy", "redis": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "redis": "disconnected", "error": str(e)}
```

### **Railway Logs Monitoring**
```bash
# Check Redis connection in logs
railway logs --filter="Redis connection"
railway logs --filter="celery"
```

The fix ensures Celery properly connects to Railway Redis instead of trying to use localhost, with robust error handling and connection retry logic.
