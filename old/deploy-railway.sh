#!/bin/bash

# Railway Deployment Script
# Simple deployment to Railway cloud platform

echo "🚀 Deploying to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📥 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Login to Railway
echo "🔐 Please login to Railway..."
railway login

# Link to project or create new one
if [ ! -f "railway.toml" ]; then
    echo "📦 Creating new Railway project..."
    railway link
else
    echo "🔗 Using existing Railway project..."
fi

# Deploy the application
echo "🚀 Deploying application..."
railway up

# Show deployment info
echo "✅ Deployment complete!"
echo "🌐 Your app is deploying to Railway"
echo "📚 Check Railway dashboard for deployment URL"
echo "⚡ Services included: FastAPI + Redis + Celery Worker"
