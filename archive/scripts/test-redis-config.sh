#!/bin/bash

echo "🔧 Redis Database Configuration Check"
echo "===================================="
echo "Checking if API and Worker are using the same Redis database"
echo

# Check API Redis configuration
echo "1️⃣ API Redis Configuration:"
echo "==========================="
aws ecs describe-task-definition --task-definition accunode-api:5 --region us-east-1 \
  --query 'taskDefinition.containerDefinitions[0].environment[?contains(name, `REDIS`)]' \
  --output table

echo
echo "2️⃣ Worker Redis Configuration:"
echo "=============================="
aws ecs describe-task-definition --task-definition accunode-worker:2 --region us-east-1 \
  --query 'taskDefinition.containerDefinitions[0].environment[?contains(name, `REDIS`)]' \
  --output table

echo
echo "3️⃣ Testing Redis Connection Compatibility:"
echo "=========================================="

# Get the exact Redis URLs from both services
API_REDIS=$(aws ecs describe-task-definition --task-definition accunode-api:5 --region us-east-1 \
  --query 'taskDefinition.containerDefinitions[0].environment[?name==`REDIS_URL`].value' --output text)

WORKER_REDIS=$(aws ecs describe-task-definition --task-definition accunode-worker:2 --region us-east-1 \
  --query 'taskDefinition.containerDefinitions[0].environment[?name==`REDIS_URL`].value' --output text)

echo "API Redis URL: $API_REDIS"
echo "Worker Redis URL: $WORKER_REDIS"

if [ "$API_REDIS" = "$WORKER_REDIS" ]; then
    echo "✅ Redis URLs match between API and Worker"
else
    echo "❌ Redis URLs don't match!"
    echo "This would prevent job communication"
fi

echo
echo "4️⃣ Checking Database Numbers:"
echo "=========================="
API_DB=$(aws ecs describe-task-definition --task-definition accunode-api:5 --region us-east-1 \
  --query 'taskDefinition.containerDefinitions[0].environment[?name==`REDIS_DB`].value' --output text)

WORKER_DB=$(aws ecs describe-task-definition --task-definition accunode-worker:2 --region us-east-1 \
  --query 'taskDefinition.containerDefinitions[0].environment[?name==`REDIS_DB`].value' --output text)

echo "API Redis DB: $API_DB"
echo "Worker Redis DB: $WORKER_DB"

if [ "$API_DB" = "$WORKER_DB" ]; then
    echo "✅ Redis database numbers match"
else
    echo "❌ Redis database numbers don't match!"
    echo "This would prevent job communication"
fi

echo
echo "5️⃣ Live Worker Monitoring Test:"
echo "=============================="
echo "Starting real-time worker monitoring..."
echo "Now go to your frontend and create a job!"
echo "Press Ctrl+C to stop monitoring"
echo
echo "🔍 Watching worker logs..."

# Monitor worker logs in real-time
aws logs tail /ecs/accunode-worker --follow --region us-east-1
