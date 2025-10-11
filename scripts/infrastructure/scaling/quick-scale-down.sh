#!/bin/bash

# Quick ECS-Only Scale Down (Partial Savings)
# Use when you want to save costs but keep database running
# Savings: $1.24/day (keeps RDS/bastion for quick development restarts)

echo "🔻 Quick ECS scale down (keeping database running)..."

# Scale ECS Services to 0
aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --desired-count 0
aws ecs update-service --cluster AccuNode-Production --service accunode-worker-service --desired-count 0

echo "✅ ECS Services scaled down!"
echo "💰 Savings: $1.24/day"
echo "🗄️ Database and bastion remain available for quick restart"
echo ""
echo "🌐 BASTION HOST IP INFORMATION:"
echo "==============================="

# Get bastion host IP information (stays running during quick scale)
BASTION_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PublicIpAddress' --output text)
BASTION_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PrivateIpAddress' --output text)

echo "📍 Public IP:  $BASTION_PUBLIC_IP  (← Still running - same IP)"
echo "🏠 Private IP: $BASTION_PRIVATE_IP"
echo ""
echo "💡 Bastion Host remains accessible for database management"
echo "🔐 SSH: ssh -i bastion-access-key.pem ec2-user@$BASTION_PUBLIC_IP"
