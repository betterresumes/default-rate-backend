#!/bin/bash

# Railway Production Deployment Script
echo "🚀 Deploying to Railway Production..."

# Check if railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI is not installed. Please install it first:"
    echo "npm install -g @railway/cli"
    exit 1
fi

# Check if logged in to Railway
if ! railway auth &> /dev/null; then
    echo "❌ Not logged in to Railway. Please login first:"
    echo "railway login"
    exit 1
fi

echo "🔧 Preparing for Railway deployment..."

# Create .railwayignore if it doesn't exist
if [ ! -f .railwayignore ]; then
    echo "📝 Creating .railwayignore file..."
    cat > .railwayignore << 'EOF'
.git
.github
.env.local
.env.example
old/
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
.pytest_cache/
.coverage
htmlcov/
.tox/
.nox/
coverage.xml
*.cover
.hypothesis/
.DS_Store
docker-compose.local.yml
Dockerfile.local
scripts/deploy-local.sh
scripts/start-local.sh
scripts/start-local-worker.sh
README.md
doc.md
EOF
fi

echo "🏗️ Building production image..."

# Deploy to Railway
echo "🚀 Deploying to Railway..."
railway deploy

echo "✅ Deployment initiated!"
echo ""
echo "🔗 Useful Railway commands:"
echo "  - Check status: railway status"
echo "  - View logs: railway logs"
echo "  - Open dashboard: railway open"
echo "  - Set environment variables: railway env set KEY=value"
echo ""
echo "📋 Required environment variables for Railway:"
echo "  - DATABASE_URL (PostgreSQL connection string)"
echo "  - REDIS_URL (Redis connection string)"
echo "  - SECRET_KEY (32+ character secret key)"
echo "  - SMTP_USERNAME, SMTP_PASSWORD (Email credentials)"
echo "  - CORS_ORIGIN (Frontend domain)"
echo ""
echo "🎯 Railway Services to Deploy:"
echo "  1. FastAPI Server (this repository)"
echo "  2. PostgreSQL Database (Railway add-on)"
echo "  3. Redis (Railway add-on)"  
echo "  4. Celery Worker (deploy this repository with worker command)"
