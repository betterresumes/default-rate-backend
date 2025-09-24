#!/bin/bash
# Bulk Upload Test Script - Annual Predictions
# User: Super Admin - can upload system-wide data
# File: test_annual_250_rows.csv

API_BASE="http://localhost:8000/api/v1"

echo "🔐 Authenticating as super_admin (admin@defaultrate.com)..."

# Get access token
TOKEN_RESPONSE=$(curl -s -X POST "$API_BASE/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@defaultrate.com" \
  -d "password=admin123" \
  -d "grant_type=password")

# Extract token
ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$ACCESS_TOKEN" ]; then
    echo "❌ Authentication failed!"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful!"
echo "🚀 Starting bulk upload for annual predictions..."

# Upload annual predictions
UPLOAD_RESPONSE=$(curl -s -X POST "$API_BASE/predictions/annual/bulk-upload-async" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@test_annual_250_rows.csv")

echo "📊 Upload Response:"
echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"

# Extract job_id for status checking
JOB_ID=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))")

if [ ! -z "$JOB_ID" ]; then
    echo "\n🔍 Checking job status..."
    sleep 2
    
    STATUS_RESPONSE=$(curl -s -X GET "$API_BASE/predictions/jobs/$JOB_ID/status" \
      -H "Authorization: Bearer $ACCESS_TOKEN")
    
    echo "📋 Job Status:"
    echo "$STATUS_RESPONSE" | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))"
fi

echo "\n✅ Annual bulk upload test completed for super_admin!"
