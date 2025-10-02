#!/bin/bash

echo "🔧 Testing Worker with Real Job Creation"
echo "========================================"
echo "Using credentials: patilpranit3112@gmail.com"
echo "Testing with real Excel file upload"
echo

# API Base URL
API_URL="https://d3tytmnn6rkqkb.cloudfront.net"

echo "1️⃣ Logging in to get access token..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patilpranit3112@gmail.com",
    "password": "Test123*"
  }')

echo "Login response:"
echo "$LOGIN_RESPONSE" | jq . 2>/dev/null || echo "$LOGIN_RESPONSE"

# Extract access token
ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ "$ACCESS_TOKEN" = "null" ] || [ "$ACCESS_TOKEN" = "" ]; then
    echo "❌ Login failed. Cannot proceed with job test."
    echo "Response: $LOGIN_RESPONSE"
    exit 1
fi

echo "✅ Login successful! Access token obtained."

echo
echo "2️⃣ Testing quarterly bulk upload (simulating Excel file)..."

# Use one of the quarterly Excel files as reference for data structure
# Create a small test job first
TEST_JOB_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/predictions/quarterly/bulk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "companies": [
      {
        "symbol": "AAPL",
        "name": "Apple Inc",
        "market_cap": 2500000000000,
        "current_ratio": 1.2,
        "debt_to_equity": 0.8,
        "return_on_equity": 0.15,
        "return_on_assets": 0.08,
        "asset_turnover": 0.53,
        "inventory_turnover": 12.5,
        "receivables_turnover": 8.9,
        "operating_margin": 0.25,
        "net_margin": 0.20
      },
      {
        "symbol": "GOOGL", 
        "name": "Alphabet Inc",
        "market_cap": 1800000000000,
        "current_ratio": 2.8,
        "debt_to_equity": 0.3,
        "return_on_equity": 0.18,
        "return_on_assets": 0.12,
        "asset_turnover": 0.67,
        "inventory_turnover": 15.2,
        "receivables_turnover": 6.4,
        "operating_margin": 0.22,
        "net_margin": 0.18
      }
    ]
  }')

echo "Job creation response:"
echo "$TEST_JOB_RESPONSE" | jq . 2>/dev/null || echo "$TEST_JOB_RESPONSE"

# Extract job ID
JOB_ID=$(echo "$TEST_JOB_RESPONSE" | jq -r '.job_id' 2>/dev/null)

if [ "$JOB_ID" = "null" ] || [ "$JOB_ID" = "" ]; then
    echo "❌ Job creation failed!"
    echo "Response: $TEST_JOB_RESPONSE"
else
    echo "✅ Job created successfully! Job ID: $JOB_ID"
    
    echo
    echo "3️⃣ Monitoring job status and worker logs..."
    echo "===========================================" 
    
    # Check job status
    for i in {1..10}; do
        echo "Checking job status ($i/10)..."
        JOB_STATUS=$(curl -s "$API_URL/api/v1/predictions/jobs/$JOB_ID" \
          -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.status' 2>/dev/null)
        
        echo "Job Status: $JOB_STATUS"
        
        if [ "$JOB_STATUS" = "completed" ]; then
            echo "🎉 Job completed successfully!"
            break
        elif [ "$JOB_STATUS" = "failed" ]; then
            echo "❌ Job failed!"
            break
        elif [ "$JOB_STATUS" = "processing" ]; then
            echo "⏳ Job is being processed by worker..."
        fi
        
        sleep 3
    done
    
    echo
    echo "4️⃣ Final job details:"
    curl -s "$API_URL/api/v1/predictions/jobs/$JOB_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN" | jq . 2>/dev/null
fi

echo
echo "🔍 Check worker logs for job processing activity!"
