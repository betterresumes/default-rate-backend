# 🚂 Railway Deployment Fix

## ❌ **Problem**
Railway deployment was failing with this error:
```
chmod: cannot access 'scripts/start-railway.sh': No such file or directory
chmod: cannot access 'scripts/start-worker.sh': No such file or directory
```

## ✅ **Root Cause**
The Dockerfile and Railway configuration files were referencing scripts in the wrong location:
- **Looking for**: `scripts/start-railway.sh` 
- **Actually located**: `deployment/scripts/start-railway.sh`

## 🔧 **Files Fixed**

### 1. **Dockerfile**
```dockerfile
# BEFORE (❌)
RUN chmod +x scripts/start-railway.sh scripts/start-worker.sh
CMD ["./scripts/start-railway.sh"]

# AFTER (✅)  
RUN chmod +x deployment/scripts/start-railway.sh deployment/scripts/start-worker.sh
CMD ["./deployment/scripts/start-railway.sh"]
```

### 2. **deployment/scripts/start-railway.sh**
```bash
# BEFORE (❌)
exec uvicorn src.app:app

# AFTER (✅)
exec uvicorn app.main:app
```

### 3. **deployment/railway/railway.toml**
```toml
# BEFORE (❌)
[deploy]
startCommand = "./scripts/start-railway.sh"

[services.worker]
deploy.startCommand = "./scripts/start-worker.sh"

# AFTER (✅)
[deploy]
startCommand = "./deployment/scripts/start-railway.sh"

[services.worker]
deploy.startCommand = "./deployment/scripts/start-worker.sh"
```

### 4. **deployment/railway/railway-worker.toml**
```toml
# BEFORE (❌)
[deploy]
startCommand = "./scripts/start-worker.sh"

# AFTER (✅)
[deploy]
startCommand = "./deployment/scripts/start-worker.sh"
```

## 🚀 **Railway Deployment Instructions**

### **Method 1: Using Railway CLI**
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Deploy from project root
railway up
```

### **Method 2: Using Railway Dashboard**
1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Create new project
3. Connect your GitHub repository
4. Railway will automatically use the `Dockerfile`

### **Method 3: Using railway.toml (Recommended)**
1. Copy `deployment/railway/railway.toml` to project root:
```bash
cp deployment/railway/railway.toml railway.toml
```

2. Deploy:
```bash
railway up
```

## 🔄 **For Celery Workers (Optional)**

If you need background job processing, deploy a separate worker service:

1. Copy worker configuration:
```bash
cp deployment/railway/railway-worker.toml railway.toml
```

2. Create separate Railway service
3. Deploy with worker configuration

## 📋 **Environment Variables Needed**

Set these in Railway dashboard:

### **Required:**
```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
JWT_SECRET=your-jwt-secret-key
```

### **Optional (for Celery):**
```bash
REDIS_URL=redis://user:pass@host:port
CELERY_BROKER_URL=$REDIS_URL
CELERY_RESULT_BACKEND=$REDIS_URL
```

### **Production Settings:**
```bash
DEBUG=false
CORS_ORIGIN=https://your-frontend-domain.com
PYTHONUNBUFFERED=1
PYTHONPATH=/app
```

## 🏥 **Health Check**

The app includes a health check endpoint at `/health`:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
```

Railway will automatically use this for health monitoring.

## 🎯 **Next Steps**

1. **Commit these fixes**:
```bash
git add .
git commit -m "Fix Railway deployment script paths and app imports"
git push origin main
```

2. **Deploy to Railway**:
```bash
railway up
```

3. **Monitor deployment**:
```bash
railway status
railway logs
```

## 🔍 **Troubleshooting**

### **If build still fails:**
1. Check Railway logs: `railway logs`
2. Verify all scripts have execute permissions
3. Ensure `requirements.prod.txt` exists and is correct

### **If app doesn't start:**
1. Check that `app/main.py` contains the FastAPI app instance
2. Verify environment variables are set
3. Check health endpoint: `https://your-app.railway.app/health`

### **If imports fail:**
1. Verify `PYTHONPATH=/app` is set
2. Check that `app/__init__.py` exists
3. Ensure all required dependencies are in `requirements.prod.txt`

## ✅ **Expected Result**

After these fixes, Railway deployment should:
1. ✅ Build successfully without chmod errors
2. ✅ Start the FastAPI server on the correct port
3. ✅ Respond to health checks at `/health`
4. ✅ Serve the API at your Railway domain

The deployment error should be completely resolved!
