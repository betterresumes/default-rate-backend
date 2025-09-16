#!/bin/bash

# Production Deployment Script for Docker Compose
# This script deploys your FastAPI app with Redis and Celery worker

echo "🚀 Starting Production Deployment..."

# 1. Pull latest code
git pull origin main

# 2. Build and start all services
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# 3. Check service health
echo "⏳ Waiting for services to start..."
sleep 30

# 4. Verify all services are running
echo "📊 Service Status:"
docker-compose ps

# 5. Check logs
echo "� Recent logs:"
docker-compose logs --tail=50

# 6. Test API health
echo "🩺 Health Check:"
curl -f http://localhost:8000/health || echo "❌ API health check failed"

echo "✅ Deployment complete!"
echo "🌐 API: http://your-domain.com:8000"
echo "📚 Docs: http://your-domain.com:8000/docs"
    railway init
fi

# Add PostgreSQL database
echo "🗄️ Adding PostgreSQL database..."
railway add postgresql

# Deploy the application
echo "🚀 Deploying to Railway..."
railway up

echo "✅ Deployment complete!"
echo "🌐 Your app will be available at: https://your-app-name.railway.app"
echo "📊 Check logs with: railway logs"
echo "🔧 Manage your app at: https://railway.app/dashboard"
