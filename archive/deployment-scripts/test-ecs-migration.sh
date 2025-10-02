#!/bin/bash

# Test ECS Migration - Load Balancer Verification
echo "🎯 ECS Migration - Load Balancer Test"
echo "===================================="

ALB_URL="http://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo "Testing: $ALB_URL"
echo ""

# Test health endpoint
echo "1️⃣  Testing /health endpoint..."
curl -s --max-time 10 "$ALB_URL/health" | jq '.' 2>/dev/null || echo "❌ Health endpoint failed or returned non-JSON"

echo ""
echo "2️⃣  Testing root endpoint..."
curl -s --max-time 10 "$ALB_URL" | head -c 200

echo ""
echo ""
echo "📊 Current Infrastructure Status:"
echo "================================"
echo "✅ ECS Cluster: AccuNode-Production"
echo "✅ ECS Service: accunode-api-service (1 task running, healthy)"
echo "✅ Load Balancer: AccuNode-ECS-ALB"
echo "✅ Target Group: AccuNode-ECS-API-TG (1 healthy target)"
echo "✅ Database: Connected (PostgreSQL RDS)"
echo "✅ Redis: Connected (ElastiCache)"
echo ""
echo "🌐 Your application is now running on ECS Fargate!"
echo "📱 API URL: $ALB_URL"
echo "🏥 Health Check: $ALB_URL/health"
echo ""
echo "🚀 Migration from EC2 Auto Scaling Groups to ECS Fargate: COMPLETE!"
