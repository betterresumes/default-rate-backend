#!/bin/bash

# Test quarterly processing with debug version
CLOUDFRONT_URL="https://d3tytmnn6rkqkb.cloudfront.net/api/v1"

echo "🔐 Getting authentication token..."
LOGIN_RESPONSE=$(curl -s -X POST "$CLOUDFRONT_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patilpranit3112@gmail.com",
    "password": "Test123*"
  }')

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.access_token')

if [ "$ACCESS_TOKEN" = "null" ] || [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Login failed:"
    echo $LOGIN_RESPONSE | jq '.'
    exit 1
fi

echo "✅ Authentication successful!"

# Test quarterly upload with small data set for debugging
echo ""
echo "🧪 Testing quarterly processing with debug logging..."
QUARTERLY_TEST=$(curl -s -X POST "$CLOUDFRONT_URL/quarterly/bulk-upload-async" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "data": [
      {
        "company_symbol": "DEBUG1",
        "company_name": "Debug Test Company 1",
        "year": 2025,
        "quarter": 1,
        "total_debt_to_ebitda": 5.5,
        "sga_margin": 25.0,
        "long_term_debt_to_total_capital": 45.0,
        "return_on_capital": 12.5
      },
      {
        "company_symbol": "DEBUG2", 
        "company_name": "Debug Test Company 2",
        "year": 2025,
        "quarter": 1,
        "total_debt_to_ebitda": 7.2,
        "sga_margin": 30.5,
        "long_term_debt_to_total_capital": 55.0,
        "return_on_capital": 8.3
      }
    ]
  }')

echo "Response: $QUARTERLY_TEST"

QUARTERLY_JOB_ID=$(echo $QUARTERLY_TEST | jq -r '.job_id')
QUARTERLY_TASK_ID=$(echo $QUARTERLY_TEST | jq -r '.task_id')

echo "📋 Job Details:"
echo "   Job ID: $QUARTERLY_JOB_ID"
echo "   Task ID: $QUARTERLY_TASK_ID"

if [ "$QUARTERLY_JOB_ID" != "null" ] && [ ! -z "$QUARTERLY_JOB_ID" ]; then
    echo ""
    echo "⏳ Monitoring job progress..."
    
    for i in {1..12}; do
        sleep 10
        echo "🔍 Check #$i (${i}0 seconds):"
        
        STATUS_RESPONSE=$(curl -s "$CLOUDFRONT_URL/quarterly/job-status/$QUARTERLY_JOB_ID" \
          -H "Authorization: Bearer $ACCESS_TOKEN")
        
        STATUS=$(echo $STATUS_RESPONSE | jq -r '.status // "unknown"')
        PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress // 0')
        
        echo "   Status: $STATUS | Progress: $PROGRESS%"
        
        if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ] || [ "$STATUS" = "error" ]; then
            echo ""
            echo "🏁 Final Status:"
            echo $STATUS_RESPONSE | jq '.'
            break
        fi
        
        if [ $i -eq 12 ]; then
            echo ""
            echo "⏰ Timeout reached after 2 minutes. Final status:"
            echo $STATUS_RESPONSE | jq '.'
        fi
    done
else
    echo "❌ Failed to create job"
fi

echo ""
echo "📊 ECS Service Status:"
aws ecs describe-services --cluster AccuNode-Production --services accunode-worker-service --region us-east-1 \
  --query 'services[0].deployments[0].{Status:status,RolloutState:rolloutState,TaskDef:taskDefinition,RunningCount:runningCount}'

echo ""
echo "📝 Recent Worker Logs (if available):"
TASK_ARN=$(aws ecs list-tasks --cluster AccuNode-Production --service-name accunode-worker-service --region us-east-1 --query 'taskArns[0]' --output text 2>/dev/null)

if [ "$TASK_ARN" != "None" ] && [ ! -z "$TASK_ARN" ]; then
    TASK_ID=$(echo $TASK_ARN | cut -d'/' -f3)
    echo "Task ID: $TASK_ID"
    
    # Get recent logs
    aws logs filter-log-events --log-group-name "/ecs/accunode-worker" --region us-east-1 \
      --start-time $(date -v-5M +%s)000 \
      --filter-pattern "$TASK_ID" \
      --query 'events[*].message' --output text | tail -20
else
    echo "No active worker task found"
fi
