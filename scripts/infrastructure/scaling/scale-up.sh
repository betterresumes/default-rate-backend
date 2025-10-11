#!/bin/bash

# Complete Development Environment Scale Up
# Run this when you start working
# Restores full development environment

echo "🔺 Starting up COMPLETE development environment..."

# 1. Start Bastion Host first (fastest)
echo "💻 Starting bastion host..."
aws ec2 start-instances --instance-ids i-079307078ef4436bd

# 2. Start RDS Database (takes longest)
echo "🗄️ Starting RDS database (this takes 3-5 minutes)..."
aws rds start-db-instance --db-instance-identifier accunode-postgres

# 3. Start ECS Services
echo "📦 Scaling up ECS services..."
aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --desired-count 1
aws ecs update-service --cluster AccuNode-Production --service accunode-worker-service --desired-count 1

echo ""
echo "⏳ Waiting for all services to become ready..."
echo "   - Bastion Host: ~1-2 minutes"
echo "   - RDS Database: ~3-5 minutes"  
echo "   - ECS Services: ~2-3 minutes"
echo ""

# Monitor RDS startup
echo "📊 Monitoring RDS startup..."
while true; do
    RDS_STATUS=$(aws rds describe-db-instances --db-instance-identifier accunode-postgres --query 'DBInstances[0].DBInstanceStatus' --output text)
    
    if [ "$RDS_STATUS" == "available" ]; then
        echo "✅ RDS Database is ready!"
        break
    else
        echo "⏳ RDS Status: $RDS_STATUS (waiting for 'available')"
        sleep 30
    fi
done

# Monitor ECS startup
echo "📊 Monitoring ECS startup..."
while true; do
    RUNNING_TASKS=$(aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service --query 'sum(services[*].runningCount)')
    
    if [ "$RUNNING_TASKS" == "2" ]; then
        echo "✅ ECS Services are ready!"
        break
    else
        echo "⏳ ECS Services starting... ($RUNNING_TASKS/2 running)"
        sleep 30
    fi
done

# Check Bastion Host
BASTION_STATE=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[0].Instances[0].State.Name' --output text)
echo "✅ Bastion Host: $BASTION_STATE"

echo ""
echo "🚀 COMPLETE DEVELOPMENT ENVIRONMENT IS READY!"
echo "📱 Your application is fully accessible"
echo "🗄️ Database connections available via bastion host"

# Show final status
echo ""
echo "📈 Final infrastructure status:"
aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service --query 'services[*].{Service:serviceName, Desired:desiredCount, Running:runningCount}' --output table

echo ""
echo "🌐 BASTION HOST IP INFORMATION:"
echo "==============================="

# Get bastion host IP information
BASTION_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PublicIpAddress' --output text)
BASTION_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PrivateIpAddress' --output text)

echo "🖥️  Bastion Host Access Details:"
echo "   📍 Public IP:  $BASTION_PUBLIC_IP  (← NEW IP for SSH access)"
echo "   🏠 Private IP: $BASTION_PRIVATE_IP (← Same private IP)"
echo ""
echo "📋 SSH Connection Commands:"
echo "   🔐 Direct SSH:"
echo "      ssh -i bastion-access-key.pem ec2-user@$BASTION_PUBLIC_IP"
echo ""
echo "   🗄️ Database Tunnel:"  
echo "      ssh -i bastion-access-key.pem -L 5432:accunode-postgres.cluster-xyz.us-east-1.rds.amazonaws.com:5432 ec2-user@$BASTION_PUBLIC_IP"
echo ""
echo "💡 IMPORTANT: Save this Public IP ($BASTION_PUBLIC_IP) - it changes every restart!"
echo "🔄 This IP will be different next time you run scale-up.sh"
