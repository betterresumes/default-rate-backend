#!/bin/bash
# Curl requests for Quarterly Bulk Upload API Testing
# Updated with your new bearer token

BASE_URL="http://localhost:8000"
BEARER_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4MjAxMTZhYS01M2VjLTRhOTEtOGNmOS0zZmI5MWJhMjQ4MDYiLCJleHAiOjE3NTkwMDE1MzZ9.jFdZ88Bn4NCD_a0Im7OyQ1LwH-pbQfsp1mIl2dx6pXg"

echo "🚀 QUARTERLY BULK UPLOAD API TESTING"
echo "====================================="

# Test 1: quarterly_predictions_q1_batch.xlsx
echo ""
echo "📊 Test 1: Q1 Batch File"
echo "File: quarterly_predictions_q1_batch.xlsx"
echo "Endpoint: /api/v1/predictions/quarterly/bulk-upload-async"
echo ""
echo "Curl command:"
echo "curl -X POST \"${BASE_URL}/api/v1/predictions/quarterly/bulk-upload-async\" \\"
echo "  -H \"Authorization: Bearer ${BEARER_TOKEN}\" \\"
echo "  -F \"file=@data/others/quarterly_predictions_q1_batch.xlsx\""
echo ""

# Test 2: quarterly_predictions_final_batch.xlsx
echo "📊 Test 2: Final Batch File"
echo "File: quarterly_predictions_final_batch.xlsx"
echo "Endpoint: /api/v1/predictions/quarterly/bulk-upload-async"
echo ""
echo "Curl command:"
echo "curl -X POST \"${BASE_URL}/api/v1/predictions/quarterly/bulk-upload-async\" \\"
echo "  -H \"Authorization: Bearer ${BEARER_TOKEN}\" \\"
echo "  -F \"file=@data/others/quarterly_predictions_final_batch.xlsx\""
echo ""

# Test 3: With response formatting
echo "📊 Test 3: Q2 Batch with JSON formatting"
echo "File: quarterly_predictions_q2_batch.xlsx"
echo ""
echo "Curl command with formatted JSON response:"
echo "curl -X POST \"${BASE_URL}/api/v1/predictions/quarterly/bulk-upload-async\" \\"
echo "  -H \"Authorization: Bearer ${BEARER_TOKEN}\" \\"
echo "  -F \"file=@data/others/quarterly_predictions_q2_batch.xlsx\" \\"
echo "  | jq '.'"
echo ""

# Test 4: With verbose output for debugging
echo "📊 Test 4: Q3 Batch with verbose debugging"
echo "File: quarterly_predictions_q3_batch.xlsx"
echo ""
echo "Curl command with verbose output:"
echo "curl -v -X POST \"${BASE_URL}/api/v1/predictions/quarterly/bulk-upload-async\" \\"
echo "  -H \"Authorization: Bearer ${BEARER_TOKEN}\" \\"
echo "  -F \"file=@data/others/quarterly_predictions_q3_batch.xlsx\""
echo ""

# Test 5: Save response to file
echo "📊 Test 5: Q4 Batch with response saved to file"
echo "File: quarterly_predictions_q4_batch.xlsx"
echo ""
echo "Curl command saving response:"
echo "curl -X POST \"${BASE_URL}/api/v1/predictions/quarterly/bulk-upload-async\" \\"
echo "  -H \"Authorization: Bearer ${BEARER_TOKEN}\" \\"
echo "  -F \"file=@data/others/quarterly_predictions_q4_batch.xlsx\" \\"
echo "  -o quarterly_upload_response.json"
echo ""

echo "💡 TIPS:"
echo "- Run these commands from the backend directory"
echo "- The response will include a job_id to track progress"
echo "- Use the job_id to check status with:"
echo "  curl -H \"Authorization: Bearer ${BEARER_TOKEN}\" \\"
echo "    \"${BASE_URL}/api/v1/predictions/bulk-upload/job/{JOB_ID}/status\""
echo ""

echo "🔍 Expected Response Format:"
echo "{"
echo "  \"success\": true,"
echo "  \"message\": \"Bulk upload job started successfully\","
echo "  \"job_id\": \"abc123-def456-ghi789\","
echo "  \"task_id\": \"celery-task-id\","
echo "  \"total_rows\": 20,"
echo "  \"estimated_time_minutes\": 1.5"
echo "}"
