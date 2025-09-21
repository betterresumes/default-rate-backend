# Render Deployment Guide - Default Rate Prediction API

This guide provides step-by-step instructions for deploying the Default Rate Prediction API to Render.com.

## 🏗️ Architecture Overview

The application consists of:
- **FastAPI Backend**: Multi-tenant prediction API with authentication
- **PostgreSQL Database**: Main application database
- **Redis**: Background task queue and caching
- **Celery Workers**: Background processing for bulk uploads
- **Static File Storage**: For ML models and uploaded files

## 📋 Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Domain** (optional): For custom domain setup

## 🔧 Step 1: Environment Variables

Create these environment variables in your Render services:

### Core Configuration
```bash
# Application
ENVIRONMENT=production
DEBUG=false
API_VERSION=v1
APP_NAME="Default Rate Prediction API"

# Server
HOST=0.0.0.0
PORT=8000
UVICORN_WORKERS=4

# Security
SECRET_KEY=your-super-secret-key-here-minimum-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### Database Configuration
```bash
# PostgreSQL (will be provided by Render PostgreSQL service)
DATABASE_URL=postgresql://username:password@hostname:port/database
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=default_rate_db
POSTGRES_HOST=your_postgres_host
POSTGRES_PORT=5432
```

### Redis Configuration
```bash
# Redis (will be provided by Render Redis service)
REDIS_URL=redis://hostname:port
REDIS_HOST=your_redis_host
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password
```

### Celery Configuration
```bash
# Background Tasks
CELERY_BROKER_URL=redis://hostname:port
CELERY_RESULT_BACKEND=redis://hostname:port
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
CELERY_ACCEPT_CONTENT=["json"]
CELERY_TIMEZONE=UTC
```

### Email Configuration (Optional)
```bash
# Email settings for notifications
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
```

## 🗃️ Step 2: Create PostgreSQL Database

1. **In Render Dashboard**:
   - Click "New +" → "PostgreSQL"
   - Name: `default-rate-db`
   - Database Name: `default_rate_db`
   - User: `default_rate_user`
   - Region: Choose closest to your users
   - Plan: Select based on your needs (Free tier available)

2. **Get Database Connection Details**:
   - After creation, note the connection details
   - Copy the `DATABASE_URL` for use in web service

## 💾 Step 3: Create Redis Instance

1. **In Render Dashboard**:
   - Click "New +" → "Redis"
   - Name: `default-rate-redis`
   - Region: Same as your database
   - Plan: Select based on your needs

2. **Get Redis Connection Details**:
   - Copy the `REDIS_URL` for use in services

## 🚀 Step 4: Deploy Web Service (FastAPI)

1. **Create Web Service**:
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Name: `default-rate-api`
   - Region: Same as database
   - Branch: `main` (or your production branch)

2. **Configure Build & Deploy**:
   ```bash
   # Build Command
   pip install --upgrade pip && pip install -r requirements.prod.txt
   
   # Start Command
   uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 4
   ```

3. **Environment Variables**:
   - Add all the environment variables listed in Step 1
   - Use the actual DATABASE_URL and REDIS_URL from your services

4. **Advanced Settings**:
   - Python Version: `3.11`
   - Plan: Select based on your needs
   - Auto-Deploy: Enable for automatic deployments

## 🔄 Step 5: Deploy Celery Worker Service

1. **Create Background Worker**:
   - Click "New +" → "Background Worker"
   - Connect same GitHub repository
   - Name: `default-rate-worker`
   - Region: Same as other services

2. **Configure Worker**:
   ```bash
   # Build Command
   pip install --upgrade pip && pip install -r requirements.prod.txt
   
   # Start Command
   celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
   ```

3. **Environment Variables**:
   - Add the same environment variables as the web service
   - Celery workers need access to database and Redis

## 📊 Step 6: Deploy Celery Beat (Optional - for scheduled tasks)

If you have scheduled tasks, create a separate service:

1. **Create Background Worker**:
   - Click "New +" → "Background Worker"
   - Name: `default-rate-beat`

2. **Configure Beat**:
   ```bash
   # Build Command
   pip install --upgrade pip && pip install -r requirements.prod.txt
   
   # Start Command
   celery -A app.workers.celery_app beat --loglevel=info
   ```

## 🔧 Step 7: Database Migrations

After deployment, initialize your database:

1. **Access Web Service Shell**:
   - Go to your web service dashboard
   - Click "Shell" tab
   - Run migrations:

```bash
# Initialize database tables
python -c "from app.core.database import create_tables; create_tables()"

# Create initial super admin (optional)
python scripts/create_admin.py
```

## 🌐 Step 8: Custom Domain (Optional)

1. **Add Custom Domain**:
   - In web service settings → "Custom Domains"
   - Add your domain
   - Configure DNS records as instructed

2. **SSL Certificate**:
   - Render automatically provides SSL certificates
   - No additional configuration needed

## 📊 Step 9: Monitoring and Scaling

### Health Checks
Render automatically monitors your services. Your FastAPI app includes:
- Health check endpoint: `/health`
- Metrics endpoint: `/metrics` (if implemented)

### Scaling
- **Web Service**: Adjust instance type in settings
- **Workers**: Increase concurrency or add more worker instances
- **Database**: Upgrade plan for more connections/storage

### Logs
- Access logs in each service dashboard
- Set up log forwarding if needed

## 🔐 Step 10: Security Considerations

1. **Environment Variables**:
   - Never commit secrets to code
   - Use Render's environment variable encryption

2. **Network Security**:
   - Services communicate over private network
   - Database only accessible to your services

3. **SSL/TLS**:
   - Automatic HTTPS for all services
   - Force HTTPS redirects in production

## 📱 Step 11: Testing Deployment

1. **Health Check**:
   ```bash
   curl https://your-app-name.onrender.com/health
   ```

2. **API Documentation**:
   ```bash
   https://your-app-name.onrender.com/docs
   ```

3. **Authentication Test**:
   ```bash
   curl -X POST https://your-app-name.onrender.com/api/v1/auth/register \
   -H "Content-Type: application/json" \
   -d '{"email":"test@example.com","password":"testpass123"}'
   ```

## 🚨 Common Issues & Solutions

### Database Connection Issues
```bash
# Check DATABASE_URL format
postgresql://username:password@hostname:port/database

# Ensure all database environment variables are set
```

### Redis Connection Issues
```bash
# Check REDIS_URL format
redis://hostname:port

# Verify Redis service is running
```

### Worker Not Processing Tasks
```bash
# Check worker logs
# Ensure CELERY_BROKER_URL matches REDIS_URL
# Verify worker service is running
```

### Performance Issues
```bash
# Increase worker concurrency
# Upgrade service plans
# Optimize database queries
```

## 📈 Cost Optimization

1. **Free Tier Limits**:
   - Web services sleep after 15 minutes of inactivity
   - PostgreSQL: 1GB storage, 97 hours/month
   - Redis: 25MB storage, 30 days

2. **Paid Plans**:
   - Always-on services
   - More resources and storage
   - Better performance guarantees

## 🔧 Maintenance

1. **Updates**:
   - Push to connected branch for auto-deployment
   - Monitor deployment logs

2. **Database Backups**:
   - Render provides automatic backups
   - Can create manual backups in dashboard

3. **Monitoring**:
   - Check service health regularly
   - Monitor error logs and performance metrics

## 📞 Support

- **Render Documentation**: [render.com/docs](https://render.com/docs)
- **Community**: [community.render.com](https://community.render.com)
- **Status Page**: [status.render.com](https://status.render.com)

---

## 🏁 Quick Deployment Checklist

- [ ] Create PostgreSQL database
- [ ] Create Redis instance
- [ ] Deploy web service with correct environment variables
- [ ] Deploy Celery worker service
- [ ] Run database migrations
- [ ] Test API endpoints
- [ ] Configure custom domain (optional)
- [ ] Set up monitoring and alerts

Your Default Rate Prediction API should now be live on Render! 🎉
