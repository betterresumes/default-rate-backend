#!/bin/bash

# Complete Load Balancer Setup for ECS Migration
# This script creates ALB, Target Group, Listener, and connects to ECS

set -e
export AWS_DEFAULT_REGION=us-east-1

echo "🚀 Starting Complete Load Balancer Setup"
echo "========================================"

# Function to check if resource exists
check_resource() {
    local resource_type=$1
    local resource_name=$2
    echo "🔍 Checking if $resource_type '$resource_name' exists..."
}

# 1. Check/Create Target Group
echo "📝 Step 1: Target Group Configuration"
echo "--------------------------------"

TG_EXISTS=$(aws elbv2 describe-target-groups --names "AccuNode-ECS-API-TG" 2>/dev/null || echo "NOT_FOUND")

if [[ "$TG_EXISTS" == "NOT_FOUND" ]]; then
    echo "Creating Target Group: AccuNode-ECS-API-TG"
    
    TG_ARN=$(aws elbv2 create-target-group \
        --name "AccuNode-ECS-API-TG" \
        --protocol HTTP \
        --port 8000 \
        --vpc-id vpc-0cd7231cf6acb1d4f \
        --target-type ip \
        --health-check-enabled \
        --health-check-path "/health" \
        --health-check-interval-seconds 30 \
        --health-check-timeout-seconds 5 \
        --healthy-threshold-count 2 \
        --unhealthy-threshold-count 3 \
        --matcher HttpCode=200 \
        --query 'TargetGroups[0].TargetGroupArn' --output text)
    
    echo "✅ Target Group Created: $TG_ARN"
else
    TG_ARN=$(echo "$TG_EXISTS" | jq -r '.TargetGroups[0].TargetGroupArn')
    echo "✅ Target Group Already Exists: $TG_ARN"
fi

# 2. Get Load Balancer ARN
echo -e "\n📝 Step 2: Load Balancer Configuration"
echo "--------------------------------"

ALB_ARN=$(aws elbv2 describe-load-balancers --names "AccuNode-ECS-ALB" --query 'LoadBalancers[0].LoadBalancerArn' --output text)
ALB_DNS=$(aws elbv2 describe-load-balancers --names "AccuNode-ECS-ALB" --query 'LoadBalancers[0].DNSName' --output text)

echo "✅ Load Balancer ARN: $ALB_ARN"
echo "✅ Load Balancer DNS: $ALB_DNS"

# 3. Check/Create Listener
echo -e "\n📝 Step 3: Listener Configuration"
echo "--------------------------------"

LISTENER_EXISTS=$(aws elbv2 describe-listeners --load-balancer-arn "$ALB_ARN" 2>/dev/null || echo "NOT_FOUND")

if [[ "$LISTENER_EXISTS" == "NOT_FOUND" ]] || [[ $(echo "$LISTENER_EXISTS" | jq '.Listeners | length') -eq 0 ]]; then
    echo "Creating HTTP Listener..."
    
    LISTENER_ARN=$(aws elbv2 create-listener \
        --load-balancer-arn "$ALB_ARN" \
        --protocol HTTP \
        --port 80 \
        --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
        --query 'Listeners[0].ListenerArn' --output text)
    
    echo "✅ Listener Created: $LISTENER_ARN"
else
    LISTENER_ARN=$(echo "$LISTENER_EXISTS" | jq -r '.Listeners[0].ListenerArn')
    echo "✅ Listener Already Exists: $LISTENER_ARN"
fi

# 4. Update ECS Service to use Load Balancer
echo -e "\n📝 Step 4: ECS Service Integration"
echo "--------------------------------"

echo "Updating ECS API Service to use Load Balancer..."

aws ecs update-service \
    --cluster AccuNode-Production \
    --service accunode-api-service \
    --load-balancers targetGroupArn="$TG_ARN",containerName=accunode-api,containerPort=8000 \
    --health-check-grace-period-seconds 300

echo "✅ ECS Service Updated with Load Balancer"

# 5. Display Summary
echo -e "\n🎉 Load Balancer Setup Complete!"
echo "================================"
echo "📍 Application URL: http://$ALB_DNS"
echo "📍 Health Check: http://$ALB_DNS/health"
echo "📍 Target Group: AccuNode-ECS-API-TG"
echo "📍 Listener: HTTP:80 -> ECS:8000"
echo ""
echo "🔄 The ECS service is now configured with the load balancer."
echo "⏰ Wait 2-3 minutes for targets to register and become healthy."
echo ""
echo "📊 To check target health:"
echo "aws elbv2 describe-target-health --target-group-arn '$TG_ARN'"
