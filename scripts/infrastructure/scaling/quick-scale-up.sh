#!/bin/bash

# Quick ECS-Only Scale Up (Fast Development Start)
# Use when database is already running
# Startup time: 2-3 minutes

echo "🔺 Quick ECS scale up (database already running)..."

# Scale ECS Services to 1
aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --desired-count 1
aws ecs update-service --cluster AccuNode-Production --service accunode-worker-service --desired-count 1

echo "⏳ Starting ECS services (2-3 minutes)..."

# Wait for ECS services
while true; do
    RUNNING_TASKS=$(aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service --query 'sum(services[*].runningCount)')
    
    if [ "$RUNNING_TASKS" == "2" ]; then
        echo "✅ Development environment ready!"
        break
    else
        echo "⏳ Services starting... ($RUNNING_TASKS/2 running)"
        sleep 30
    fi
done

echo ""
echo "🚀 Ready to develop!"
echo ""
echo "🌐 BASTION HOST IP INFORMATION:"
echo "==============================="

# Get bastion host IP information (should be same as before since we didn't stop it)
BASTION_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PublicIpAddress' --output text)
BASTION_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PrivateIpAddress' --output text)

echo "📍 Public IP:  $BASTION_PUBLIC_IP  (← Same IP - bastion stayed running)"
echo "🏠 Private IP: $BASTION_PRIVATE_IP"
echo ""
echo "📋 SSH Connection Commands:"
echo "   🔐 Direct SSH:"
echo "      ssh -i bastion-access-key.pem ec2-user@$BASTION_PUBLIC_IP"
echo ""
echo "   🗄️ Database Tunnel:"  
echo "      ssh -i bastion-access-key.pem -L 5432:accunode-postgres.cluster-xyz.us-east-1.rds.amazonaws.com:5432 ec2-user@$BASTION_PUBLIC_IP"
