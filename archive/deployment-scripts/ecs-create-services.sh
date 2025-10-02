#!/bin/bash

# ECS Services Creation Script
set -e

echo "🚀 AccuNode ECS Services Creation"
echo "================================="
echo "Date: $(date)"
echo

# Configuration
REGION="us-east-1"
CLUSTER_NAME="AccuNode-Production"
VPC_ID="vpc-0cd7231cf6acb1d4f"
SUBNET_1="subnet-0582605386f26e006"
SUBNET_2="subnet-0f58ba551b23d56c6"

# Get security group ID (create if needed)
echo "🔐 Step 1: Setting up Security Groups"
echo "====================================="

# Check if ECS security group exists
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=AccuNode-ECS-SG" --query 'SecurityGroups[0].GroupId' --output text --region $REGION 2>/dev/null)

if [ "$SG_ID" = "None" ] || [ -z "$SG_ID" ]; then
    echo "🔒 Creating ECS security group..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name "AccuNode-ECS-SG" \
        --description "Security group for AccuNode ECS tasks" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' --output text)
    
    # Add inbound rules
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 8000 \
        --cidr 10.0.0.0/16 \
        --region $REGION
    
    # Add outbound rules for database and Redis
    aws ec2 authorize-security-group-egress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 5432 \
        --cidr 10.0.0.0/16 \
        --region $REGION
        
    aws ec2 authorize-security-group-egress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 6379 \
        --cidr 10.0.0.0/16 \
        --region $REGION
    
    echo "✅ Security group created: $SG_ID"
else
    echo "✅ Using existing security group: $SG_ID"
fi

# Step 2: Create ECS Services
echo
echo "📋 Step 2: Creating ECS Services"
echo "==============================="

# Create API Service
echo "🌐 Creating API Service..."
aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name "accunode-api-service" \
    --task-definition "accunode-api:1" \
    --desired-count 1 \
    --launch-type "FARGATE" \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --region $REGION > /tmp/api-service-result.json

echo "✅ API Service created"

# Create Worker Service
echo "⚡ Creating Worker Service..."
aws ecs create-service \
    --cluster $CLUSTER_NAME \
    --service-name "accunode-worker-service" \
    --task-definition "accunode-worker:1" \
    --desired-count 1 \
    --launch-type "FARGATE" \
    --network-configuration "awsvpcConfiguration={subnets=[$SUBNET_1,$SUBNET_2],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
    --region $REGION > /tmp/worker-service-result.json

echo "✅ Worker Service created"

echo
echo "🎉 ECS Services Created Successfully!"
echo "===================================="
echo "API Service: accunode-api-service"
echo "Worker Service: accunode-worker-service"
echo "Security Group: $SG_ID"
echo
echo "📋 Next Steps:"
echo "1. Wait for tasks to start (2-3 minutes)"
echo "2. Configure load balancer integration"
echo "3. Set up auto scaling"
echo
echo "Check status with: aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service --region us-east-1"
