#!/bin/bash

# Railway Deployment Script
# Automated deployment to Railway with Neon PostgreSQL

set -e  # Exit on any error

echo "🚀 Starting Railway deployment..."

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    curl -fsSL https://railway.app/install.sh | sh
fi

# Login to Railway (if not already logged in)
echo "🔐 Checking Railway authentication..."
railway whoami || {
    echo "Please login to Railway:"
    railway login
}

# Check if we're in a Railway project
if ! railway status &> /dev/null; then
    echo "🔗 Linking to Railway project..."
    railway link
fi

# Set environment variables if they don't exist
echo "⚙️ Setting up environment variables..."

# Check for critical environment variables
if ! railway variables get DATABASE_URL &> /dev/null; then
    echo "⚠️  DATABASE_URL not set. Please set it manually:"
    echo "railway variables set DATABASE_URL='postgresql://user:pass@host/db?sslmode=require'"
fi

if ! railway variables get SECRET_KEY &> /dev/null; then
    echo "🔑 Generating SECRET_KEY..."
    SECRET_KEY=$(openssl rand -hex 32)
    railway variables set SECRET_KEY="$SECRET_KEY"
fi

if ! railway variables get JWT_SECRET_KEY &> /dev/null; then
    echo "🔑 Generating JWT_SECRET_KEY..."
    JWT_SECRET_KEY=$(openssl rand -hex 32)
    railway variables set JWT_SECRET_KEY="$JWT_SECRET_KEY"
fi

# Set basic configuration
railway variables set ENVIRONMENT="production"
railway variables set DEBUG="false"
railway variables set API_V1_STR="/api/v1"
railway variables set PROJECT_NAME="Default Rate API"
railway variables set PYTHONPATH="/app"
railway variables set PYTHONUNBUFFERED="1"

echo "📦 Deploying to Railway..."
railway up

echo "✅ Deployment completed!"
echo "🌐 Your app will be available at the Railway URL shown above."

# Show status
railway status
