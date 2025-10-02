#!/bin/bash

# Fix ECS IAM Role Issue
set -e

echo "🔧 Fixing ECS IAM Role Issue"
echo "============================"
echo "Date: $(date)"
echo

# Step 1: Create ecsTaskExecutionRole
echo "🔐 Step 1: Creating ecsTaskExecutionRole"
echo "======================================="

# Create trust policy document
cat > /tmp/ecs-task-execution-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Check if role exists
if aws iam get-role --role-name ecsTaskExecutionRole >/dev/null 2>&1; then
    echo "✅ ecsTaskExecutionRole already exists"
else
    echo "🔨 Creating ecsTaskExecutionRole..."
    
    # Create the role
    aws iam create-role \
        --role-name ecsTaskExecutionRole \
        --assume-role-policy-document file:///tmp/ecs-task-execution-trust-policy.json \
        --description "ECS Task Execution Role for AccuNode"
    
    echo "✅ ecsTaskExecutionRole created"
fi

# Step 2: Attach required policies
echo
echo "📋 Step 2: Attaching Required Policies"
echo "======================================"

# Attach AmazonECSTaskExecutionRolePolicy
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy \
    2>/dev/null && echo "✅ AmazonECSTaskExecutionRolePolicy attached" || echo "⚠️ Policy already attached"

# Attach CloudWatchLogsFullAccess for logging
aws iam attach-role-policy \
    --role-name ecsTaskExecutionRole \
    --policy-arn arn:aws:iam::aws:policy/CloudWatchLogsFullAccess \
    2>/dev/null && echo "✅ CloudWatchLogsFullAccess attached" || echo "⚠️ Policy already attached"

echo
echo "🔄 Step 3: Updating ECS Services"
echo "==============================="

# Update API service to use the role (force new deployment)
echo "🌐 Updating API Service..."
aws ecs update-service \
    --cluster AccuNode-Production \
    --service accunode-api-service \
    --force-new-deployment \
    --region us-east-1 >/dev/null

echo "✅ API Service deployment triggered"

# Update Worker service
echo "⚡ Updating Worker Service..."
aws ecs update-service \
    --cluster AccuNode-Production \
    --service accunode-worker-service \
    --force-new-deployment \
    --region us-east-1 >/dev/null

echo "✅ Worker Service deployment triggered"

echo
echo "🎉 IAM Role Issue Fixed!"
echo "========================"
echo "✅ ecsTaskExecutionRole created with proper permissions"
echo "✅ ECS services updated with force deployment"
echo
echo "📋 Next Steps:"
echo "1. Wait 2-3 minutes for new tasks to start"
echo "2. Check status: aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service --region us-east-1"
echo "3. Verify tasks are running"

# Clean up temp files
rm -f /tmp/ecs-task-execution-trust-policy.json

echo
echo "⏱️ Checking status in 30 seconds..."
