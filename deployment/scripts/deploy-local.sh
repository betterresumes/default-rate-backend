#!/bin/bash

# Local Development Deployment Script
echo "🚀 Setting up Local Development Environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create .env.local if it doesn't exist
if [ ! -f .env.local ]; then
    echo "📝 Creating .env.local file..."
    cp .env.local .env.local.backup 2>/dev/null || true
fi

echo "🔧 Building and starting local development environment..."

# Stop any existing containers
echo "🛑 Stopping existing containers..."
docker-compose -f docker-compose.local.yml down

# Build and start services
echo "🏗️ Building Docker images..."
docker-compose -f docker-compose.local.yml build

echo "🚀 Starting services..."
docker-compose -f docker-compose.local.yml up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
docker-compose -f docker-compose.local.yml ps

echo "✅ Local development environment is ready!"
echo ""
echo "🌐 Services available at:"
echo "  - API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - pgAdmin: http://localhost:8080 (admin@example.com / admin123)"
echo "  - Redis Commander: http://localhost:8081"
echo ""
echo "📋 Useful commands:"
echo "  - View logs: docker-compose -f docker-compose.local.yml logs -f"
echo "  - Stop services: docker-compose -f docker-compose.local.yml down"
echo "  - Restart services: docker-compose -f docker-compose.local.yml restart"
