#!/bin/bash

# Complete Development Environment Scale Down
# Run this when you stop working for the day
# MAXIMUM COST SAVINGS: ~$2.15/day

echo "🔻 Scaling down ENTIRE development environment..."

# 1. Scale ECS Services to 0
echo "📦 Scaling ECS services to 0..."
aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --desired-count 0
aws ecs update-service --cluster AccuNode-Production --service accunode-worker-service --desired-count 0

# 2. Stop RDS Database (BIGGEST SAVINGS)
echo "🗄️ Stopping RDS database..."
aws rds stop-db-instance --db-instance-identifier accunode-postgres

# 3. Stop Bastion Host
echo "💻 Stopping bastion host..."
aws ec2 stop-instances --instance-ids i-079307078ef4436bd

echo ""
echo "✅ COMPLETE ENVIRONMENT SCALED DOWN!"
echo "💰 Daily cost savings breakdown:"
echo "   - ECS Services: $1.24/day"
echo "   - RDS Database: $0.72/day"  
echo "   - Bastion Host: $0.19/day"
echo "   - TOTAL SAVINGS: $2.15/day"
echo ""
echo "📊 Services still running (unavoidable):"
echo "   - ElastiCache Redis: $0.31/day"
echo "   - Application Load Balancer: $0.44/day"
echo "   - VPC Infrastructure: $0.75/day"
echo "   - Remaining daily cost: ~$1.50/day"
echo ""
echo "⚠️  NOTE: RDS auto-restarts after 7 days if not manually started"

echo ""
echo "🌐 CURRENT BASTION HOST IP (Before Shutdown):"
echo "=============================================="

# Get current bastion host IP information before stopping
CURRENT_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PublicIpAddress' --output text)
CURRENT_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PrivateIpAddress' --output text)

echo "📍 Current Public IP:  $CURRENT_PUBLIC_IP"
echo "🏠 Current Private IP: $CURRENT_PRIVATE_IP"
echo ""
echo "⚠️  IMPORTANT: After next scale-up, the Public IP will be DIFFERENT!"
echo "💡 You'll need to run scale-up.sh to get the new Public IP"

# Show final status
echo ""
echo "📈 Checking final status..."
aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service --query 'services[*].{Service:serviceName, Desired:desiredCount, Running:runningCount}' --output table
