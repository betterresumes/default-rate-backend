#!/bin/bash

echo "🔍 Celery Worker Troubleshooting"
echo "================================="
echo "Date: $(date)"
echo

# Get current task IDs
API_TASK=$(aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-api-service --region us-east-1 --query 'taskArns[0]' --output text | cut -d'/' -f3)
WORKER_TASK=$(aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-worker-service --region us-east-1 --query 'taskArns[0]' --output text | cut -d'/' -f3)

echo "API Task: $API_TASK"
echo "Worker Task: $WORKER_TASK"
echo

# Test 1: Check if jobs are being created in Redis
echo "1️⃣ Testing Job Creation in Redis:"
echo "================================="
echo "Making a test API call to check if jobs are queued..."

# Create a simple test job via API
TEST_RESPONSE=$(curl -s -X POST 'https://d3tytmnn6rkqkb.cloudfront.net/api/v1/predictions/quarterly/bulk' \
  -H 'Content-Type: application/json' \
  -d '{"companies": [{"symbol": "AAPL", "name": "Apple Inc", "market_cap": 2500000000000, "current_ratio": 1.2, "debt_to_equity": 0.8}]}' \
  --max-time 30 || echo "API_ERROR")

if [ "$TEST_RESPONSE" != "API_ERROR" ]; then
    echo "✅ API Response received:"
    echo "$TEST_RESPONSE" | jq . 2>/dev/null || echo "$TEST_RESPONSE"
    
    JOB_ID=$(echo "$TEST_RESPONSE" | jq -r '.job_id' 2>/dev/null)
    if [ "$JOB_ID" != "null" ] && [ "$JOB_ID" != "" ]; then
        echo "📋 Job ID: $JOB_ID"
    fi
else
    echo "❌ API call failed"
fi

echo

# Test 2: Check recent API logs for job creation
echo "2️⃣ Checking API Logs for Job Creation:"
echo "======================================"
API_LOGS=$(aws logs get-log-events \
  --log-group-name /ecs/accunode-api \
  --log-stream-name ecs/accunode-api/$API_TASK \
  --region us-east-1 \
  --start-time $(($(date +%s) - 600))000 \
  --limit 10 \
  --query 'events[-5:].message' \
  --output text 2>/dev/null)

if [ -n "$API_LOGS" ]; then
    echo "Recent API logs:"
    echo "$API_LOGS"
else
    echo "No recent API logs found"
fi

echo

# Test 3: Check worker logs for any new activity
echo "3️⃣ Checking Worker Logs for Job Processing:"
echo "=========================================="
WORKER_LOGS=$(aws logs get-log-events \
  --log-group-name /ecs/accunode-worker \
  --log-stream-name ecs/accunode-worker/$WORKER_TASK \
  --region us-east-1 \
  --start-time $(($(date +%s) - 600))000 \
  --limit 10 \
  --query 'events[].message' \
  --output text 2>/dev/null)

if [ -n "$WORKER_LOGS" ]; then
    echo "Recent worker logs:"
    echo "$WORKER_LOGS"
else
    echo "❌ No recent worker activity - this indicates the issue!"
fi

echo

# Test 4: Check Redis connectivity from API
echo "4️⃣ Testing Redis Connectivity from API:"
echo "======================================="
HEALTH_CHECK=$(curl -s https://d3tytmnn6rkqkb.cloudfront.net/health | jq '.services.redis' 2>/dev/null)
echo "Redis Health from API: $HEALTH_CHECK"

CELERY_STATUS=$(curl -s https://d3tytmnn6rkqkb.cloudfront.net/health | jq '.services.celery' 2>/dev/null)
echo "Celery Status from API: $CELERY_STATUS"

echo

# Test 5: Possible issues analysis
echo "5️⃣ Potential Issues Analysis:"
echo "============================"
echo "Checking for common Celery worker issues..."

# Check if worker is using correct queue
echo "• Worker Queue: medium_priority (from logs)"
echo "• API should be sending jobs to: medium_priority"

# Check Redis URL consistency
echo "• Redis URL in worker: redis://accunode-redis.d9avr2.0001.use1.cache.amazonaws.com:6379"
echo "• Redis URL should match between API and Worker"

echo

echo "🔧 Diagnostic Commands:"
echo "======================="
echo "# Watch worker logs live:"
echo "aws logs tail /ecs/accunode-worker --follow --region us-east-1"
echo
echo "# Check ECS task definitions for environment variables:"
echo "aws ecs describe-task-definition --task-definition accunode-api:5 --region us-east-1 --query 'taskDefinition.containerDefinitions[0].environment[?name==\`REDIS_URL\`]'"
echo "aws ecs describe-task-definition --task-definition accunode-worker:2 --region us-east-1 --query 'taskDefinition.containerDefinitions[0].environment[?name==\`REDIS_URL\`]'"
echo
echo "# Test Redis connection manually:"
echo "curl -s https://d3tytmnn6rkqkb.cloudfront.net/health | jq '.services'"
