#!/bin/bash

# AccuNode AWS Security Groups Setup Script
# Phase 1b: Security Groups Configuration

set -e

echo "🔒 AccuNode AWS Deployment - Phase 1b: Security Groups"
echo "====================================================="

# Load infrastructure configuration
if [ ! -f "infrastructure.json" ]; then
    echo "❌ Error: infrastructure.json not found!"
    echo "   Please run 01-infrastructure.sh first"
    exit 1
fi

VPC_ID=$(cat infrastructure.json | python3 -c "import sys, json; print(json.load(sys.stdin)['vpc_id'])")
AWS_REGION=$(cat infrastructure.json | python3 -c "import sys, json; print(json.load(sys.stdin)['region'])")
PROJECT_NAME=$(cat infrastructure.json | python3 -c "import sys, json; print(json.load(sys.stdin)['project_name'])")

echo "📋 Using VPC: $VPC_ID in region $AWS_REGION"
echo ""

# Step 1: ALB Security Group (Internet-facing)
echo "🌐 Step 1: Creating ALB Security Group..."
ALB_SG=$(aws ec2 create-security-group \
    --group-name "$PROJECT_NAME-alb-sg" \
    --description "Security group for AccuNode Application Load Balancer" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $ALB_SG \
    --tags Key=Name,Value="$PROJECT_NAME-alb-sg" \
           Key=Environment,Value="production" \
    --region $AWS_REGION

# Allow HTTP and HTTPS from internet
aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG \
    --protocol tcp \
    --port 80 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION

aws ec2 authorize-security-group-ingress \
    --group-id $ALB_SG \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region $AWS_REGION

echo "✅ ALB Security Group created: $ALB_SG"

# Step 2: API Server Security Group
echo "🖥️ Step 2: Creating API Server Security Group..."
API_SG=$(aws ec2 create-security-group \
    --group-name "$PROJECT_NAME-api-sg" \
    --description "Security group for AccuNode API servers" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $API_SG \
    --tags Key=Name,Value="$PROJECT_NAME-api-sg" \
           Key=Environment,Value="production" \
    --region $AWS_REGION

# Allow HTTP from ALB only
aws ec2 authorize-security-group-ingress \
    --group-id $API_SG \
    --protocol tcp \
    --port 8000 \
    --source-group $ALB_SG \
    --region $AWS_REGION

# Allow SSH access (optional, for debugging)
aws ec2 authorize-security-group-ingress \
    --group-id $API_SG \
    --protocol tcp \
    --port 22 \
    --cidr 10.0.0.0/16 \
    --region $AWS_REGION

echo "✅ API Server Security Group created: $API_SG"

# Step 3: Worker Security Group
echo "👷 Step 3: Creating Worker Security Group..."
WORKER_SG=$(aws ec2 create-security-group \
    --group-name "$PROJECT_NAME-worker-sg" \
    --description "Security group for AccuNode worker nodes" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $WORKER_SG \
    --tags Key=Name,Value="$PROJECT_NAME-worker-sg" \
           Key=Environment,Value="production" \
    --region $AWS_REGION

# Allow SSH access (optional, for debugging)
aws ec2 authorize-security-group-ingress \
    --group-id $WORKER_SG \
    --protocol tcp \
    --port 22 \
    --cidr 10.0.0.0/16 \
    --region $AWS_REGION

echo "✅ Worker Security Group created: $WORKER_SG"

# Step 4: RDS Security Group
echo "🗄️ Step 4: Creating RDS Security Group..."
RDS_SG=$(aws ec2 create-security-group \
    --group-name "$PROJECT_NAME-rds-sg" \
    --description "Security group for AccuNode PostgreSQL database" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $RDS_SG \
    --tags Key=Name,Value="$PROJECT_NAME-rds-sg" \
           Key=Environment,Value="production" \
    --region $AWS_REGION

# Allow PostgreSQL from API servers and workers
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG \
    --protocol tcp \
    --port 5432 \
    --source-group $API_SG \
    --region $AWS_REGION

aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG \
    --protocol tcp \
    --port 5432 \
    --source-group $WORKER_SG \
    --region $AWS_REGION

echo "✅ RDS Security Group created: $RDS_SG"

# Step 5: Redis Security Group
echo "🔴 Step 5: Creating Redis Security Group..."
REDIS_SG=$(aws ec2 create-security-group \
    --group-name "$PROJECT_NAME-redis-sg" \
    --description "Security group for AccuNode Redis cache" \
    --vpc-id $VPC_ID \
    --query 'GroupId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $REDIS_SG \
    --tags Key=Name,Value="$PROJECT_NAME-redis-sg" \
           Key=Environment,Value="production" \
    --region $AWS_REGION

# Allow Redis from API servers and workers
aws ec2 authorize-security-group-ingress \
    --group-id $REDIS_SG \
    --protocol tcp \
    --port 6379 \
    --source-group $API_SG \
    --region $AWS_REGION

aws ec2 authorize-security-group-ingress \
    --group-id $REDIS_SG \
    --protocol tcp \
    --port 6379 \
    --source-group $WORKER_SG \
    --region $AWS_REGION

echo "✅ Redis Security Group created: $REDIS_SG"

# Step 6: Update infrastructure configuration
echo "💾 Step 6: Updating infrastructure configuration..."
python3 << EOF
import json

# Load existing config
with open('infrastructure.json', 'r') as f:
    config = json.load(f)

# Add security groups
config.update({
    "alb_security_group": "$ALB_SG",
    "api_security_group": "$API_SG", 
    "worker_security_group": "$WORKER_SG",
    "rds_security_group": "$RDS_SG",
    "redis_security_group": "$REDIS_SG"
})

# Save updated config
with open('infrastructure.json', 'w') as f:
    json.dump(config, f, indent=2)
EOF

echo "✅ Security groups configuration saved"
echo ""
echo "🎉 Phase 1b Complete! Security groups setup successful."
echo ""
echo "📋 Security Groups Summary:"
echo "   ALB SG: $ALB_SG (HTTP/HTTPS from internet)"
echo "   API SG: $API_SG (Port 8000 from ALB)"
echo "   Worker SG: $WORKER_SG (Internal access only)"
echo "   RDS SG: $RDS_SG (Port 5432 from API/Workers)"
echo "   Redis SG: $REDIS_SG (Port 6379 from API/Workers)"
echo ""
echo "⏭️ Next: Run 03-parameter-store.sh to set up secrets management"
