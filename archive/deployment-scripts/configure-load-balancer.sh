#!/bin/bash

# Configure Load Balancer for ECS Migration
set -e

echo "🔗 Configuring Load Balancer for ECS"
echo "===================================="
echo "Date: $(date)"
echo

# Configuration
REGION="us-east-1"
CLUSTER_NAME="AccuNode-Production"

# Step 1: Get current ALB information
echo "🔍 Step 1: Getting Current Load Balancer Information"
echo "=================================================="

# Get Load Balancer ARN
ALB_ARN=$(aws elbv2 describe-load-balancers --names AccuNode-ALB --region $REGION --query 'LoadBalancers[0].LoadBalancerArn' --output text 2>/dev/null)

if [ "$ALB_ARN" = "None" ] || [ -z "$ALB_ARN" ]; then
    # Try to find ALB by DNS name
    ALB_ARN=$(aws elbv2 describe-load-balancers --region $REGION --query 'LoadBalancers[?contains(DNSName, `AccuNode-ALB`) || contains(LoadBalancerName, `AccuNode`)].LoadBalancerArn' --output text 2>/dev/null | head -1)
fi

if [ "$ALB_ARN" = "None" ] || [ -z "$ALB_ARN" ]; then
    echo "❌ Could not find AccuNode ALB. Let's list all load balancers:"
    aws elbv2 describe-load-balancers --region $REGION --query 'LoadBalancers[*].{Name:LoadBalancerName,DNS:DNSName,Scheme:Scheme}' --output table
    echo "Please check the load balancer name and update the script."
    exit 1
else
    echo "✅ Found Load Balancer: $ALB_ARN"
fi

# Get VPC from ALB
VPC_ID=$(aws elbv2 describe-load-balancers --load-balancer-arns $ALB_ARN --region $REGION --query 'LoadBalancers[0].VpcId' --output text)
echo "📍 VPC ID: $VPC_ID"

# Step 2: Create new target group for ECS
echo
echo "🎯 Step 2: Creating ECS Target Group"
echo "==================================="

# Create target group for ECS API service
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
    --health-check-timeout-seconds 10 \
    --healthy-threshold-count 2 \
    --unhealthy-threshold-count 3 \
    --region $REGION \
    --query 'TargetGroups[0].TargetGroupArn' --output text 2>/dev/null)

if [ $? -eq 0 ] && [ "$TG_ARN" != "None" ]; then
    echo "✅ Created ECS Target Group: $TG_ARN"
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

# Step 3: Update ECS API Service to use the target group
echo
echo "🔗 Step 3: Connecting ECS API Service to Load Balancer"
echo "===================================================="

# Update ECS service with load balancer configuration
aws ecs update-service \
    --cluster $CLUSTER_NAME \
    --service accunode-api-service \
    --load-balancers targetGroupArn=$TG_ARN,containerName=accunode-api,containerPort=8000 \
    --region $REGION >/dev/null

echo "✅ ECS API Service connected to Target Group"

# Step 4: Get current listener and update rules
echo
echo "📋 Step 4: Updating Load Balancer Listener Rules"
echo "=============================================="

# Get listener ARN (assuming port 80)
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --region $REGION --query 'Listeners[?Port==`80`].ListenerArn' --output text)

if [ "$LISTENER_ARN" != "None" ] && [ ! -z "$LISTENER_ARN" ]; then
    echo "✅ Found Listener: $LISTENER_ARN"
    
    # Get existing rules
    echo "📜 Current listener rules:"
    aws elbv2 describe-rules --listener-arn $LISTENER_ARN --region $REGION --query 'Rules[*].{Priority:Priority,Actions:Actions[0].TargetGroupArn}' --output table
    
    # Update default action to point to ECS target group
    echo "🔄 Updating default action to ECS target group..."
    aws elbv2 modify-listener \
        --listener-arn $LISTENER_ARN \
        --default-actions Type=forward,TargetGroupArn=$TG_ARN \
        --region $REGION >/dev/null
    
    echo "✅ Listener updated to forward traffic to ECS"
else
    echo "❌ Could not find listener on port 80"
fi

echo
echo "🎉 Load Balancer Configuration Complete!"
echo "======================================="
echo "✅ ECS Target Group created and configured"
echo "✅ ECS API Service connected to Load Balancer"
echo "✅ Load Balancer routing updated to ECS"
echo
echo "📋 Next Steps:"
echo "1. Wait 2-3 minutes for health checks to pass"
echo "2. Test Load Balancer endpoint"
echo "3. Verify ECS tasks are healthy"
echo "4. Set up auto scaling"
echo "5. Terminate old EC2 instances"
echo
echo "🔍 Check target health:"
echo "aws elbv2 describe-target-health --target-group-arn $TG_ARN --region $REGION"
