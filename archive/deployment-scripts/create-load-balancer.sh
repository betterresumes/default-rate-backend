#!/bin/bash

# Create Complete Load Balancer Setup for ECS
set -e

echo "🏗️ Creating Load Balancer for ECS Setup"
echo "======================================="
echo "Date: $(date)"
echo

# Configuration
REGION="us-east-1"
CLUSTER_NAME="AccuNode-Production"
VPC_ID="vpc-0cd7231cf6acb1d4f"
SUBNET_1="subnet-0582605386f26e006" 
SUBNET_2="subnet-0f58ba551b23d56c6"

# Step 1: Create Application Load Balancer
echo "🚀 Step 1: Creating Application Load Balancer"
echo "============================================="

# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
    --name "AccuNode-ECS-ALB" \
    --subnets $SUBNET_1 $SUBNET_2 \
    --security-groups sg-0904e16e00d5e08c7 \
    --scheme internet-facing \
    --type application \
    --ip-address-type ipv4 \
    --region $REGION \
    --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)

if [ $? -eq 0 ] && [ "$ALB_ARN" != "None" ]; then
    echo "✅ Created Load Balancer: $ALB_ARN"
    
    # Get DNS name
    ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --region $REGION --query 'LoadBalancers[0].DNSName' --output text)
    echo "🌐 Load Balancer DNS: $ALB_DNS"
else
    echo "⚠️ Load balancer might already exist. Checking for existing one..."
    ALB_ARN=$(aws elbv2 describe-load-balancers --names "AccuNode-ECS-ALB" --region $REGION --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)
    if [ "$ALB_ARN" != "None" ] && [ ! -z "$ALB_ARN" ]; then
        echo "✅ Using existing Load Balancer: $ALB_ARN"
        ALB_DNS=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --region $REGION --query 'LoadBalancers[0].DNSName' --output text)
        echo "🌐 Load Balancer DNS: $ALB_DNS"
    else
        echo "❌ Failed to create or find load balancer"
        exit 1
    fi
fi

# Step 2: Create Target Group for ECS
echo
echo "🎯 Step 2: Creating Target Group for ECS"
echo "========================================"

TG_ARN=$(aws elbv2 create-target-group \
    --name "AccuNode-ECS-API-TG" \
    --protocol HTTP \
    --port 8000 \
    --vpc-id $VPC_ID \
    --target-type ip \
    --health-check-enabled \
    --health-check-interval-seconds 30 \
    --health-check-path "/health" \
    --health-check-protocol HTTP \
    --health-check-port 8000 \
    --health-check-timeout-seconds 10 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --matcher HttpCode=200 \
    --region $REGION \
    --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)

if [ $? -eq 0 ] && [ "$TG_ARN" != "None" ]; then
    echo "✅ Created Target Group: $TG_ARN"
else
    echo "⚠️ Target group might already exist. Trying to find existing one..."
    TG_ARN=$(aws elbv2 describe-target-groups --names "AccuNode-ECS-API-TG" --region $REGION --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)
    if [ "$TG_ARN" != "None" ] && [ ! -z "$TG_ARN" ]; then
        echo "✅ Using existing Target Group: $TG_ARN"
    else
        echo "❌ Failed to create or find target group"
        exit 1
    fi
fi

# Step 3: Create Listener
echo
echo "👂 Step 3: Creating Listener"
echo "============================"

LISTENER_ARN=$(aws elbv2 create-listener \
    --load-balancer-arn $ALB_ARN \
    --protocol HTTP \
    --port 80 \
    --default-actions Type=forward,TargetGroupArn=$TG_ARN \
    --region $REGION \
    --query 'Listeners[0].ListenerArn' --output text 2>/dev/null)

if [ $? -eq 0 ] && [ "$LISTENER_ARN" != "None" ]; then
    echo "✅ Created Listener: $LISTENER_ARN"
else
    echo "⚠️ Listener might already exist"
fi

# Step 4: Update ECS API Service with Load Balancer
echo
echo "🔗 Step 4: Connecting ECS Service to Load Balancer"
echo "================================================="

# Update ECS service to include load balancer configuration
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service accunode-api-service \
    --load-balancers targetGroupArn=$TG_ARN,containerName=accunode-api,containerPort=8000 \
    --health-check-grace-period-seconds 300 \
    --region $REGION >/dev/null

echo "✅ ECS API Service connected to Load Balancer"

echo
echo "🎉 Load Balancer Setup Complete!"
echo "================================"
echo "✅ Application Load Balancer: $ALB_DNS"
echo "✅ Target Group configured for ECS"
echo "✅ Listener created on port 80"
echo "✅ ECS API Service connected"
echo
echo "📋 Next Steps:"
echo "1. Wait 3-5 minutes for health checks to pass"
echo "2. Test endpoint: http://$ALB_DNS/health"
echo "3. Verify ECS tasks are healthy"
echo
echo "🔍 Monitor target health:"
echo "aws elbv2 describe-target-health --target-group-arn $TG_ARN --region $REGION"

# Save important values for future reference
echo
echo "📝 Important Information:"
echo "========================"
echo "Load Balancer ARN: $ALB_ARN"
echo "Target Group ARN: $TG_ARN" 
echo "Listener ARN: $LISTENER_ARN"
echo "Load Balancer DNS: $ALB_DNS"
