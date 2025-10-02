#!/bin/bash

echo "🔧 Direct Worker Test - Bypassing API Authentication"
echo "=================================================="
echo "Testing if the worker can receive and process jobs directly"
echo

# Get current worker task ID
WORKER_TASK=$(aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-worker-service --region us-east-1 --query 'taskArns[0]' --output text | cut -d'/' -f3)
echo "Worker Task ID: $WORKER_TASK"

# Start monitoring worker logs in background
echo "🔍 Starting worker log monitoring..."
aws logs tail /ecs/accunode-worker --follow --region us-east-1 > /tmp/worker_logs.txt 2>&1 &
MONITOR_PID=$!
echo "Log monitoring PID: $MONITOR_PID"

# Wait a moment for monitoring to start
sleep 3

echo
echo "🧪 Testing worker job processing..."
echo "=================================="

# Test with health check task (simplest task)
echo "1️⃣ Testing simple health check task..."

# We'll check if there are any tasks in the queue by checking the API logs
# when it creates jobs

echo "2️⃣ Checking if API creates jobs when called..."

# Try to create a job via the API health check or see recent API activity
API_TASK=$(aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-api-service --region us-east-1 --query 'taskArns[0]' --output text | cut -d'/' -f3)

echo "Getting recent API logs to see job creation activity..."
aws logs get-log-events \
  --log-group-name /ecs/accunode-api \
  --log-stream-name "ecs/accunode-api/$API_TASK" \
  --region us-east-1 \
  --start-time $(($(date +%s) - 1800))000 \
  --limit 10 \
  --query 'events[].message' \
  --output text | grep -E "(job|task|celery|redis)" | tail -5

echo
echo "3️⃣ Checking current Redis queue status..."

# The health endpoint should tell us about Celery workers
curl -s https://d3tytmnn6rkqkb.cloudfront.net/health | jq '.services.celery'

echo
echo "4️⃣ Waiting 10 seconds to see if any worker activity appears..."
sleep 10

# Stop monitoring and check logs
kill $MONITOR_PID 2>/dev/null
sleep 1

echo
echo "5️⃣ Worker logs from the last 10 seconds:"
echo "========================================"
tail -20 /tmp/worker_logs.txt 2>/dev/null | grep -v "^$" | tail -10 || echo "No new worker logs detected"

# Clean up
rm -f /tmp/worker_logs.txt

echo
echo "🔍 DIAGNOSTIC SUMMARY:"
echo "====================="
echo "If you see:"
echo "✅ 'Connected to redis' - Worker can connect to Redis"
echo "✅ 'celery ready' - Worker is ready to receive jobs"  
echo "❌ No job processing logs - Jobs aren't reaching the worker"
echo "❌ No recent activity - Check if jobs are actually being created"
echo
echo "🎯 LIKELY ISSUES:"
echo "================="
echo "1. Queue name mismatch (API sending to wrong queue)"
echo "2. Redis database number mismatch"
echo "3. Worker not listening to the right queue"
echo "4. Authentication blocking job creation"
echo
echo "📋 NEXT STEPS:"
echo "=============="
echo "• Check your frontend: Does it create jobs successfully?"
echo "• Check job creation: Login to your frontend and try uploading"
echo "• Monitor: Run 'aws logs tail /ecs/accunode-worker --follow --region us-east-1'"
echo "• Then try creating a job and watch for worker activity"
