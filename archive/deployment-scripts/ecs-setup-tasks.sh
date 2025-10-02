#!/bin/bash

# ECS Deployment Script - Safe Step-by-Step Migration
set -e

echo "🚀 AccuNode ECS Migration - Step by Step"
echo "========================================"
echo "Date: $(date)"
echo

# Configuration
REGION="us-east-1"
CLUSTER_NAME="AccuNode-Production"
ECR_REPO="461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode:latest"

# Step 1: Check if cluster exists, create if needed
echo "📋 Step 1: Setting up ECS Cluster"
echo "================================="

if aws ecs describe-clusters --clusters $CLUSTER_NAME --region $REGION --query 'clusters[0].clusterName' --output text 2>/dev/null | grep -q $CLUSTER_NAME; then
    echo "✅ Cluster $CLUSTER_NAME already exists"
else
    echo "🏗️ Creating ECS cluster..."
    aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $REGION > /dev/null
    echo "✅ Cluster $CLUSTER_NAME created"
fi

# Step 2: Create CloudWatch log groups
echo
echo "📊 Step 2: Creating CloudWatch Log Groups"
echo "========================================="

aws logs create-log-group --log-group-name "/ecs/accunode-api" --region $REGION 2>/dev/null || echo "✅ API log group exists"
aws logs create-log-group --log-group-name "/ecs/accunode-worker" --region $REGION 2>/dev/null || echo "✅ Worker log group exists"

# Step 3: Register task definitions
echo
echo "📝 Step 3: Registering Task Definitions"
echo "======================================="

echo "🔄 Registering API task definition..."
aws ecs register-task-definition \
    --cli-input-json file://deployment/ecs-api-task-definition.json \
    --region $REGION > /tmp/api-task-result.json

API_TASK_ARN=$(cat /tmp/api-task-result.json | grep -o '"taskDefinitionArn":"[^"]*"' | cut -d'"' -f4)
echo "✅ API Task Definition: $API_TASK_ARN"

echo "🔄 Registering Worker task definition..."
aws ecs register-task-definition \
    --cli-input-json file://deployment/ecs-worker-task-definition.json \
    --region $REGION > /tmp/worker-task-result.json

WORKER_TASK_ARN=$(cat /tmp/worker-task-result.json | grep -o '"taskDefinitionArn":"[^"]*"' | cut -d'"' -f4)
echo "✅ Worker Task Definition: $WORKER_TASK_ARN"

echo
echo "🎉 Task Definitions Created Successfully!"
echo "========================================"
echo "API Task: $API_TASK_ARN"
echo "Worker Task: $WORKER_TASK_ARN"
echo
echo "📋 Next Steps:"
echo "1. Create ECS services"
echo "2. Configure load balancer integration"
echo "3. Set up auto scaling"
echo
echo "Run './deployment/ecs-create-services.sh' for next step"
