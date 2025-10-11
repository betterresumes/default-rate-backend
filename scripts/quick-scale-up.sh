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

echo "🚀 Ready to develop!"
