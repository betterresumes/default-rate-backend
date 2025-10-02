#!/bin/bash

echo "🧪 Testing Worker with File Upload (Correct Method)"
echo "=================================================="
echo "Creating real CSV files and uploading them to test worker"
echo

# API Base URL
API_URL="https://d3tytmnn6rkqkb.cloudfront.net"

# Create test CSV files
echo "1️⃣ Creating test CSV files..."

# Create quarterly CSV with correct format
cat > /tmp/quarterly_test.csv << EOF
company_symbol,company_name,sector,market_cap,reporting_year,reporting_quarter,total_debt_to_ebitda,sga_margin,long_term_debt_to_total_capital,return_on_capital
TSLA,Tesla Inc.,Consumer Discretionary,127606390000,2020,Q1,7.935,27.586,61.935,16.76
AAPL,Apple Inc.,Technology,2500000000000,2020,Q1,1.2,15.5,25.8,28.5
MSFT,Microsoft Corporation,Technology,1800000000000,2020,Q1,0.8,18.2,12.5,35.2
EOF

# Create annual CSV with correct format  
cat > /tmp/annual_test.csv << EOF
company_symbol,company_name,market_cap,sector,reporting_year,reporting_quarter,long_term_debt_to_total_capital,total_debt_to_ebitda,net_income_margin,ebit_to_interest_expense,return_on_assets
NKE,NIKE Inc.,100000000,Consumer Discretionary,2022,Q4,41.913,1.49,12.944,22.324,10.689
AMD,Advanced Micro Devices,85000000000,Technology,2022,Q4,15.2,0.8,18.5,45.2,15.3
INTC,Intel Corporation,180000000000,Technology,2022,Q4,25.8,2.1,15.2,18.5,12.8
EOF

echo "✅ CSV files created"

echo
echo "2️⃣ Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "patilpranit3112@gmail.com",
    "password": "Test123*"
  }')

ACCESS_TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ "$ACCESS_TOKEN" = "null" ] || [ "$ACCESS_TOKEN" = "" ]; then
    echo "❌ Login failed!"
    exit 1
fi

echo "✅ Login successful!"

echo
echo "3️⃣ Testing QUARTERLY bulk upload..."
echo "==================================="

QUARTERLY_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/predictions/quarterly/bulk-upload-async" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/tmp/quarterly_test.csv")

echo "Quarterly upload response:"
echo "$QUARTERLY_RESPONSE" | jq . 2>/dev/null || echo "$QUARTERLY_RESPONSE"

QUARTERLY_JOB_ID=$(echo "$QUARTERLY_RESPONSE" | jq -r '.job_id // .data.job_id' 2>/dev/null)

echo
echo "4️⃣ Testing ANNUAL bulk upload..."  
echo "================================"

ANNUAL_RESPONSE=$(curl -s -X POST "$API_URL/api/v1/predictions/annual/bulk-upload-async" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "file=@/tmp/annual_test.csv")

echo "Annual upload response:"
echo "$ANNUAL_RESPONSE" | jq . 2>/dev/null || echo "$ANNUAL_RESPONSE"

ANNUAL_JOB_ID=$(echo "$ANNUAL_RESPONSE" | jq -r '.job_id // .data.job_id' 2>/dev/null)

echo
echo "5️⃣ Job IDs Created:"
echo "=================="
if [ "$QUARTERLY_JOB_ID" != "null" ] && [ "$QUARTERLY_JOB_ID" != "" ]; then
    echo "📋 Quarterly Job ID: $QUARTERLY_JOB_ID"
else
    echo "❌ No quarterly job created"
fi

if [ "$ANNUAL_JOB_ID" != "null" ] && [ "$ANNUAL_JOB_ID" != "" ]; then
    echo "📋 Annual Job ID: $ANNUAL_JOB_ID"
else
    echo "❌ No annual job created"  
fi

echo
echo "6️⃣ Monitoring worker activity..."
echo "==============================="
echo "🔍 Check the worker logs terminal for job processing!"
echo "⏳ Waiting 60 seconds for jobs to process..."

# Monitor job statuses
for i in {1..12}; do
    echo "--- Status Check $i/12 ---"
    
    if [ "$QUARTERLY_JOB_ID" != "null" ] && [ "$QUARTERLY_JOB_ID" != "" ]; then
        QUARTERLY_STATUS=$(curl -s "$API_URL/api/v1/predictions/jobs/$QUARTERLY_JOB_ID" \
          -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.status' 2>/dev/null)
        echo "Quarterly Job: $QUARTERLY_STATUS"
    fi
    
    if [ "$ANNUAL_JOB_ID" != "null" ] && [ "$ANNUAL_JOB_ID" != "" ]; then
        ANNUAL_STATUS=$(curl -s "$API_URL/api/v1/predictions/jobs/$ANNUAL_JOB_ID" \
          -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.status' 2>/dev/null)
        echo "Annual Job: $ANNUAL_STATUS"
    fi
    
    sleep 5
done

echo
echo "7️⃣ Final Results:"
echo "================="
if [ "$QUARTERLY_JOB_ID" != "null" ] && [ "$QUARTERLY_JOB_ID" != "" ]; then
    echo "Quarterly Job Final Status:"
    curl -s "$API_URL/api/v1/predictions/jobs/$QUARTERLY_JOB_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
fi

if [ "$ANNUAL_JOB_ID" != "null" ] && [ "$ANNUAL_JOB_ID" != "" ]; then
    echo "Annual Job Final Status:"
    curl -s "$API_URL/api/v1/predictions/jobs/$ANNUAL_JOB_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN" | jq .
fi

# Cleanup
rm -f /tmp/quarterly_test.csv /tmp/annual_test.csv

echo
echo "🎯 WORKER TEST COMPLETE"
echo "======================"
echo "• If jobs were created but show 'pending' - worker is not processing"
echo "• If jobs show 'processing' or 'completed' - worker is working!"
echo "• Check worker logs for detailed processing information"
