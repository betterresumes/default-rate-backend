#!/bin/bash

# Quick Test Script for Annual Bulk Upload System
# This script tests the system with sample files

set -e

echo "🧪 Testing Annual Bulk Upload System..."

# Check if system is running
if ! curl -s http://localhost:8000/health > /dev/null; then
    echo "❌ System is not running. Please start it first:"
    echo "   ./start_annual_system.sh"
    exit 1
fi

# Get authentication token
echo "🔐 Getting authentication token..."
TOKEN_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"email": "patil@gmail.com", "password": "Test123*"}')

TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access_token')

if [ "$TOKEN" = "null" ]; then
    echo "❌ Authentication failed. Please check credentials in the script."
    exit 1
fi

echo "✅ Authentication successful!"

# Test with mixed quarters file
echo ""
echo "📤 Testing with mixed quarters file (Q1,Q2,Q3,Q4)..."
UPLOAD_RESPONSE=$(curl -s -X POST "http://localhost:8000/api/predictions/bulk-predict-async" \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@test_mixed_quarters.xlsx" \
    -F "prediction_type=annual")

JOB_ID=$(echo $UPLOAD_RESPONSE | jq -r '.job_id')

if [ "$JOB_ID" = "null" ]; then
    echo "❌ Upload failed:"
    echo $UPLOAD_RESPONSE
    exit 1
fi

echo "✅ Upload successful! Job ID: $JOB_ID"
echo "⏳ Waiting for processing..."

# Wait for job completion
for i in {1..10}; do
    sleep 2
    STATUS_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/predictions/job-status/$JOB_ID" \
        -H "Authorization: Bearer $TOKEN")
    
    STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
    
    if [ "$STATUS" = "SUCCESS" ]; then
        echo "✅ Processing completed!"
        
        # Show results
        echo ""
        echo "📊 Results:"
        echo $STATUS_RESPONSE | jq '.result.results[] | {stock_symbol: .stock_symbol, reporting_year: .prediction.reporting_year, reporting_quarter: .prediction.reporting_quarter}'
        
        SUCCESS_COUNT=$(echo $STATUS_RESPONSE | jq -r '.result.successful_predictions')
        FAILED_COUNT=$(echo $STATUS_RESPONSE | jq -r '.result.failed_predictions')
        
        echo ""
        echo "📈 Summary:"
        echo "   • Successful: $SUCCESS_COUNT"
        echo "   • Failed: $FAILED_COUNT"
        
        if [ "$FAILED_COUNT" = "0" ]; then
            echo "🎉 All tests passed! Annual bulk upload system is working perfectly!"
        else
            echo "⚠️  Some predictions failed. Check the results above."
        fi
        
        exit 0
    elif [ "$STATUS" = "FAILURE" ]; then
        echo "❌ Processing failed:"
        echo $STATUS_RESPONSE | jq '.error'
        exit 1
    else
        echo "⏳ Status: $STATUS (attempt $i/10)"
    fi
done

echo "⏰ Test timed out. Check job status manually:"
echo "curl -X GET \"http://localhost:8000/api/predictions/job-status/$JOB_ID\" -H \"Authorization: Bearer $TOKEN\""
