#!/bin/bash

# Check Current Infrastructure Status and IP Information
# Run this anytime to see current state and connection details

echo "🔍 INFRASTRUCTURE STATUS CHECK"
echo "=============================="
echo ""

echo "📦 ECS Services Status:"
echo "----------------------"
aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service --query 'services[*].{Service:serviceName, Desired:desiredCount, Running:runningCount, Status:status}' --output table

echo ""
echo "🗄️ RDS Database Status:"
echo "----------------------"
aws rds describe-db-instances --db-instance-identifier accunode-postgres --query 'DBInstances[*].{ID:DBInstanceIdentifier, Status:DBInstanceStatus, Endpoint:Endpoint.Address}' --output table

echo ""
echo "🖥️ Bastion Host Status:"
echo "----------------------"
aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].{InstanceId:InstanceId, State:State.Name, PublicIP:PublicIpAddress, PrivateIP:PrivateIpAddress}' --output table

echo ""
echo "🌐 CURRENT IP INFORMATION:"
echo "=========================="

# Get current bastion host details
BASTION_STATE=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[0].Instances[0].State.Name' --output text)
BASTION_PUBLIC_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PublicIpAddress' --output text)
BASTION_PRIVATE_IP=$(aws ec2 describe-instances --instance-ids i-079307078ef4436bd --query 'Reservations[*].Instances[*].PrivateIpAddress' --output text)

if [ "$BASTION_STATE" == "running" ]; then
    echo "✅ Bastion Host is RUNNING"
    echo "📍 Public IP:  $BASTION_PUBLIC_IP"
    echo "🏠 Private IP: $BASTION_PRIVATE_IP"
    echo ""
    echo "📋 SSH Connection Commands:"
    echo "   🔐 Direct SSH:"
    echo "      ssh -i bastion-access-key.pem ec2-user@$BASTION_PUBLIC_IP"
    echo ""
    echo "   🗄️ Database Tunnel:"
    echo "      ssh -i bastion-access-key.pem -L 5432:accunode-postgres.cluster-xyz.us-east-1.rds.amazonaws.com:5432 ec2-user@$BASTION_PUBLIC_IP"
    echo ""
    echo "   📊 Connect to PostgreSQL via tunnel:"
    echo "      psql -h localhost -p 5432 -U your_username -d accunode_db"
elif [ "$BASTION_STATE" == "stopped" ]; then
    echo "🛑 Bastion Host is STOPPED"
    echo "📍 Public IP: (None - will get new IP when started)"
    echo "🏠 Private IP: $BASTION_PRIVATE_IP (reserved)"
    echo ""
    echo "💡 Run './scripts/scale-up.sh' or './scripts/quick-scale-up.sh' to start services"
else
    echo "⏳ Bastion Host is in transition state: $BASTION_STATE"
    echo "📍 Public IP: $BASTION_PUBLIC_IP"
    echo "🏠 Private IP: $BASTION_PRIVATE_IP"
fi

echo ""
echo "🔗 OTHER IMPORTANT ENDPOINTS:"
echo "============================"
echo "🌐 Application Load Balancer: AccuNode-ECS-ALB.us-east-1.elb.amazonaws.com"
echo "🗄️ RDS Endpoint: accunode-postgres.cluster-xyz.us-east-1.rds.amazonaws.com:5432"
echo "🔴 Redis Endpoint: accunode-redis.d9avr2.0001.use1.cache.amazonaws.com:6379"
echo ""
echo "💰 COST STATUS:"
echo "==============="

# Get ECS service counts for cost calculation
API_COUNT=$(aws ecs describe-services --cluster AccuNode-Production --service accunode-api-service --query 'services[0].runningCount' --output text)
WORKER_COUNT=$(aws ecs describe-services --cluster AccuNode-Production --service accunode-worker-service --query 'services[0].runningCount' --output text)
RDS_STATUS=$(aws rds describe-db-instances --db-instance-identifier accunode-postgres --query 'DBInstances[0].DBInstanceStatus' --output text)

DAILY_COST=1.30  # Base cost (always running services)

if [ "$API_COUNT" != "0" ] && [ "$WORKER_COUNT" != "0" ]; then
    DAILY_COST=$(echo "$DAILY_COST + 1.24" | bc -l)
    echo "📦 ECS Services: RUNNING (+\$1.24/day)"
else
    echo "📦 ECS Services: STOPPED (saving \$1.24/day)"
fi

if [ "$RDS_STATUS" == "available" ]; then
    DAILY_COST=$(echo "$DAILY_COST + 0.72" | bc -l)
    echo "🗄️ RDS Database: RUNNING (+\$0.72/day)"
else
    echo "🗄️ RDS Database: STOPPED (saving \$0.72/day)"
fi

if [ "$BASTION_STATE" == "running" ]; then
    DAILY_COST=$(echo "$DAILY_COST + 0.19" | bc -l)
    echo "🖥️ Bastion Host: RUNNING (+\$0.19/day)"
else
    echo "🖥️ Bastion Host: STOPPED (saving \$0.19/day)"
fi

MONTHLY_COST=$(echo "$DAILY_COST * 30" | bc -l)

echo ""
echo "💵 Current Daily Cost: ~\$${DAILY_COST}"
echo "💵 Current Monthly Cost: ~\$${MONTHLY_COST}"
echo ""
echo "📊 Run this script anytime to check current status and IPs!"
