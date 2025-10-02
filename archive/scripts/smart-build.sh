#!/bin/bash

# Smart Docker Build - Only rebuild changed layers
# Reduces build time from 5 minutes to 1-2 minutes

set -e

echo "🏗️ AccuNode Smart Build System"
echo "============================="

# Configuration
ECR_REGISTRY="461962182774.dkr.ecr.us-east-1.amazonaws.com"
REPO_NAME="accunode"
REGION="us-east-1"

# Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Check what changed
echo "🔍 Analyzing changes..."

# Check if requirements changed
REQUIREMENTS_CHANGED=false
if git diff HEAD~1 --name-only | grep -q "requirements"; then
    REQUIREMENTS_CHANGED=true
    echo "📦 Requirements changed - will rebuild dependencies layer"
else
    echo "📦 Requirements unchanged - using cached dependencies"
fi

# Check if app code changed
APP_CHANGED=false
if git diff HEAD~1 --name-only | grep -q "app/\|main.py\|start.sh"; then
    APP_CHANGED=true
    echo "💻 Application code changed - will rebuild app layer"
else
    echo "💻 Application code unchanged"
fi

# Smart build strategy
if [ "$REQUIREMENTS_CHANGED" = true ]; then
    echo "🏗️ Full rebuild (requirements changed)..."
    
    # Build with cache from previous layers
    docker build \
        --cache-from $ECR_REGISTRY/$REPO_NAME:base \
        --cache-from $ECR_REGISTRY/$REPO_NAME:deps \
        --cache-from $ECR_REGISTRY/$REPO_NAME:latest \
        --target base \
        -t $ECR_REGISTRY/$REPO_NAME:base \
        -f Dockerfile.optimized .
    
    docker build \
        --cache-from $ECR_REGISTRY/$REPO_NAME:base \
        --cache-from $ECR_REGISTRY/$REPO_NAME:deps \
        --target dependencies \
        -t $ECR_REGISTRY/$REPO_NAME:deps \
        -f Dockerfile.optimized .
    
    docker build \
        --cache-from $ECR_REGISTRY/$REPO_NAME:base \
        --cache-from $ECR_REGISTRY/$REPO_NAME:deps \
        --cache-from $ECR_REGISTRY/$REPO_NAME:latest \
        -t $ECR_REGISTRY/$REPO_NAME:latest \
        -f Dockerfile.optimized .
    
    # Push all layers
    docker push $ECR_REGISTRY/$REPO_NAME:base
    docker push $ECR_REGISTRY/$REPO_NAME:deps
    docker push $ECR_REGISTRY/$REPO_NAME:latest
    
elif [ "$APP_CHANGED" = true ]; then
    echo "🏗️ Fast rebuild (only app changed)..."
    
    # Only rebuild final layer with cached dependencies
    docker build \
        --cache-from $ECR_REGISTRY/$REPO_NAME:base \
        --cache-from $ECR_REGISTRY/$REPO_NAME:deps \
        --cache-from $ECR_REGISTRY/$REPO_NAME:latest \
        -t $ECR_REGISTRY/$REPO_NAME:latest \
        -f Dockerfile.optimized .
    
    # Push only the updated final image
    docker push $ECR_REGISTRY/$REPO_NAME:latest
    
else
    echo "✅ No changes detected - using existing image"
    exit 0
fi

# Tag with commit hash for versioning
GIT_HASH=$(git rev-parse --short HEAD)
docker tag $ECR_REGISTRY/$REPO_NAME:latest $ECR_REGISTRY/$REPO_NAME:$GIT_HASH
docker push $ECR_REGISTRY/$REPO_NAME:$GIT_HASH

echo "✅ Smart build completed!"
echo "📊 Build summary:"
echo "   Latest: $ECR_REGISTRY/$REPO_NAME:latest"
echo "   Version: $ECR_REGISTRY/$REPO_NAME:$GIT_HASH"

# Estimate time saved
if [ "$REQUIREMENTS_CHANGED" = true ]; then
    echo "⏱️ Estimated time: 2-3 minutes (vs 5 minutes without cache)"
elif [ "$APP_CHANGED" = true ]; then
    echo "⏱️ Estimated time: 1 minute (vs 5 minutes full rebuild)"
fi

echo
echo "🚀 Next step: Deploy with fast-deploy.sh or update Auto Scaling launch template"
