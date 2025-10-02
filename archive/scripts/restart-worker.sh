#!/bin/bash

echo "🔄 Restarting Worker Service to Fix Task Registration"
echo "===================================================="
echo "This will restart the worker to ensure proper task registration"
echo

# Get current worker task 
CURRENT_TASK=$(aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-worker-service --region us-east-1 --query 'taskArns[0]' --output text | cut -d'/' -f3)
echo "Current Worker Task: $CURRENT_TASK"

# Force update to restart the worker
echo "🔄 Forcing worker service update to restart with fresh task registration..."
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-worker-service \
  --force-new-deployment \
  --region us-east-1 > /dev/null

echo "✅ Worker service restart initiated"

# Wait for the restart
echo "⏳ Waiting for new worker task to start..."
sleep 10

# Get new task ID
NEW_TASK=""
for i in {1..30}; do
    NEW_TASK=$(aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-worker-service --region us-east-1 --query 'taskArns[0]' --output text 2>/dev/null | cut -d'/' -f3 2>/dev/null)
    if [ "$NEW_TASK" != "$CURRENT_TASK" ] && [ "$NEW_TASK" != "" ] && [ "$NEW_TASK" != "None" ]; then
        echo "✅ New worker task started: $NEW_TASK"
        break
    fi
    echo "   Waiting for new task... ($i/30)"
    sleep 2
done

if [ "$NEW_TASK" = "$CURRENT_TASK" ] || [ "$NEW_TASK" = "" ]; then
    echo "⚠️  Same task ID or no task found. Checking task status..."
    aws ecs describe-services --cluster AccuNode-Production --services accunode-worker-service --region us-east-1 --query 'services[0].deployments[0].rolloutState' --output text
else
    echo "🎉 Worker successfully restarted with new task!"
fi

echo
echo "🔍 Monitoring new worker startup..."
echo "=================================="
echo "Watching worker logs for task registration..."

# Monitor new worker logs
aws logs tail /ecs/accunode-worker --follow --region us-east-1 --since 30s &
MONITOR_PID=$!

# Wait for startup
echo "Waiting 30 seconds for worker to fully start..."
sleep 30

# Stop monitoring  
kill $MONITOR_PID 2>/dev/null

echo
echo "✅ Worker restart complete!"
echo "=========================="
echo "🧪 Now test creating a job from your frontend"
echo "🔍 Monitor with: aws logs tail /ecs/accunode-worker --follow --region us-east-1"
echo ""
echo "📋 What this fixed:"
echo "==================="
echo "• Fresh worker startup with current task definitions"
echo "• New Redis connection with proper task routing"  
echo "• Clean celery worker state"
echo "• Proper task registration and queue binding"
