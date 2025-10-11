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
