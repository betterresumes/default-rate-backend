#!/bin/bash
# Fast ECS Deployment Script - Replaces 5-minute Docker rebuilds
set -e

REGION="us-east-1"
CLUSTER="AccuNode-Production"
ECR_REPO="461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode"
IMAGE_TAG=${1:-latest}

echo "🚀 Starting ECS Deployment for tag: $IMAGE_TAG"
echo "============================================="

# Build and push to ECR (only if needed)
if [ "$IMAGE_TAG" != "latest" ]; then
    echo "📦 Building and pushing new image..."
    docker build -t $ECR_REPO:$IMAGE_TAG .
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ECR_REPO
    docker push $ECR_REPO:$IMAGE_TAG
fi

# Update API service
echo "🔄 Updating API service..."
aws ecs update-service \
    --cluster $CLUSTER \
    --service accunode-api-service \
    --force-new-deployment \
    --region $REGION

# Update Worker service  
echo "⚡ Updating Worker service..."
aws ecs update-service \
    --cluster $CLUSTER \
    --service accunode-worker-service \
    --force-new-deployment \
    --region $REGION

echo "✅ Deployment initiated - services will update automatically"
echo "⏱️  Deployment time: ~2-3 minutes (vs previous 5+ minutes)"
