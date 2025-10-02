#!/bin/bash

# Manual Deployment Script for AccuNode
# Usage: ./deploy.sh

set -e

# Configuration
AWS_REGION="us-east-1"
ECR_REPOSITORY="accunode"
ECS_CLUSTER="AccuNode-Production"
API_SERVICE="accunode-api-service"
WORKER_SERVICE="accunode-worker-service"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting AccuNode Production Deployment${NC}"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not configured. Please run 'aws configure'${NC}"
    exit 1
fi

# Get current git commit
COMMIT_SHA=$(git rev-parse --short HEAD)
IMAGE_TAG="prod-${COMMIT_SHA}"

echo -e "${YELLOW}📦 Building image: ${IMAGE_TAG}${NC}"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push Docker image
ECR_URI=$(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY
docker build --platform linux/amd64 -t $ECR_URI:$IMAGE_TAG -t $ECR_URI:latest .
docker push $ECR_URI:$IMAGE_TAG
docker push $ECR_URI:latest

echo -e "${GREEN}✅ Image pushed successfully${NC}"

# Update ECS services
echo -e "${YELLOW}🔄 Updating ECS services...${NC}"

# Create new task definitions
aws ecs describe-task-definition --task-definition accunode-api --query 'taskDefinition' > api-task-def.json
aws ecs describe-task-definition --task-definition accunode-worker --query 'taskDefinition' > worker-task-def.json

# Update image URIs
jq --arg IMAGE "$ECR_URI:$IMAGE_TAG" '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' api-task-def.json > api-task-def-new.json
jq --arg IMAGE "$ECR_URI:$IMAGE_TAG" '.containerDefinitions[0].image = $IMAGE | del(.taskDefinitionArn, .revision, .status, .requiresAttributes, .placementConstraints, .compatibilities, .registeredAt, .registeredBy)' worker-task-def.json > worker-task-def-new.json

# Register new task definitions
API_TD_ARN=$(aws ecs register-task-definition --cli-input-json file://api-task-def-new.json --query 'taskDefinition.taskDefinitionArn' --output text)
WORKER_TD_ARN=$(aws ecs register-task-definition --cli-input-json file://worker-task-def-new.json --query 'taskDefinition.taskDefinitionArn' --output text)

# Update services
aws ecs update-service --cluster $ECS_CLUSTER --service $API_SERVICE --task-definition $API_TD_ARN --force-new-deployment
aws ecs update-service --cluster $ECS_CLUSTER --service $WORKER_SERVICE --task-definition $WORKER_TD_ARN --force-new-deployment

echo -e "${GREEN}✅ Services updated successfully${NC}"
echo -e "${YELLOW}⏳ Deployment in progress. Check ECS console for status.${NC}"

# Cleanup
rm -f api-task-def.json worker-task-def.json api-task-def-new.json worker-task-def-new.json

echo -e "${GREEN}🎉 Deployment initiated for commit ${COMMIT_SHA}${NC}"
echo -e "${YELLOW}📊 Monitor progress: https://console.aws.amazon.com/ecs/home?region=${AWS_REGION}#/clusters/${ECS_CLUSTER}/services${NC}"
