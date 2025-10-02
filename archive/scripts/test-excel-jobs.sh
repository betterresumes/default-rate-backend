#!/bin/bash

echo "🧪 Testing Worker with Real Excel File Data"
echo "==========================================="
echo "Testing both Annual and Quarterly prediction jobs"
echo "Using actual data from Excel files"
echo

# API Base URL
API_URL="https://d3tytmnn6rkqkb.cloudfront.net"

echo "1️⃣ Logging in..."
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
echo "2️⃣ Testing ANNUAL prediction job..."
echo "===================================="

# Create annual job with correct data structure (from annual_predictions_amd_fcx_ea_backup.xlsx)
ANNUAL_JOB=$(curl -s -X POST "$API_URL/api/v1/predictions/annual/bulk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "companies": [
      {
        "company_symbol": "NKE",
        "company_name": "NIKE, Inc.",
        "market_cap": 100000000,
        "sector": "Consumer Discretionary", 
        "reporting_year": 2022,
        "reporting_quarter": "Q4",
        "long_term_debt_to_total_capital": 41.913,
        "total_debt_to_ebitda": 1.49,
        "net_income_margin": 12.944,
        "ebit_to_interest_expense": 22.324,
        "return_on_assets": 10.689
      },
      {
        "company_symbol": "AMD",
        "company_name": "Advanced Micro Devices",
        "market_cap": 85000000000,
        "sector": "Technology",
        "reporting_year": 2022,
        "reporting_quarter": "Q4", 
        "long_term_debt_to_total_capital": 15.2,
        "total_debt_to_ebitda": 0.8,
        "net_income_margin": 18.5,
        "ebit_to_interest_expense": 45.2,
        "return_on_assets": 15.3
      }
    ]
  }')

echo "Annual job response:"
echo "$ANNUAL_JOB" | jq . 2>/dev/null || echo "$ANNUAL_JOB"

ANNUAL_JOB_ID=$(echo "$ANNUAL_JOB" | jq -r '.job_id' 2>/dev/null)

echo
echo "3️⃣ Testing QUARTERLY prediction job..."
echo "======================================"

# Create quarterly job with correct data structure (from quarterly_predictions_final_batch_backup.xlsx)
QUARTERLY_JOB=$(curl -s -X POST "$API_URL/api/v1/predictions/quarterly/bulk" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "companies": [
      {
        "company_symbol": "TSLA",
        "company_name": "Tesla Inc.",
        "sector": "Consumer Discretionary",
        "market_cap": 127606390000,
        "reporting_year": 2020,
        "reporting_quarter": "Q1",
        "total_debt_to_ebitda": 7.935,
        "sga_margin": 27.586,
        "long_term_debt_to_total_capital": 61.935,
        "return_on_capital": 16.76
      },
      {
        "company_symbol": "AAPL",
        "company_name": "Apple Inc.",
        "sector": "Technology",
        "market_cap": 2500000000000,
        "reporting_year": 2020,
        "reporting_quarter": "Q1",
        "total_debt_to_ebitda": 1.2,
        "sga_margin": 15.5,
        "long_term_debt_to_total_capital": 25.8,
        "return_on_capital": 28.5
      }
    ]
  }')

echo "Quarterly job response:"
echo "$QUARTERLY_JOB" | jq . 2>/dev/null || echo "$QUARTERLY_JOB"

QUARTERLY_JOB_ID=$(echo "$QUARTERLY_JOB" | jq -r '.job_id' 2>/dev/null)

echo
echo "4️⃣ Monitoring job processing..."
echo "==============================="

# Monitor both jobs
if [ "$ANNUAL_JOB_ID" != "null" ] && [ "$ANNUAL_JOB_ID" != "" ]; then
    echo "📋 Annual Job ID: $ANNUAL_JOB_ID"
fi

if [ "$QUARTERLY_JOB_ID" != "null" ] && [ "$QUARTERLY_JOB_ID" != "" ]; then
    echo "📋 Quarterly Job ID: $QUARTERLY_JOB_ID"  
fi

echo
echo "⏳ Waiting for worker to process jobs..."
echo "Check worker logs for activity!"

# Monitor job statuses
for i in {1..20}; do
    echo "--- Status Check $i/20 ---"
    
    if [ "$ANNUAL_JOB_ID" != "null" ] && [ "$ANNUAL_JOB_ID" != "" ]; then
        ANNUAL_STATUS=$(curl -s "$API_URL/api/v1/predictions/jobs/$ANNUAL_JOB_ID" \
          -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.status' 2>/dev/null)
        echo "Annual Job Status: $ANNUAL_STATUS"
    fi
    
    if [ "$QUARTERLY_JOB_ID" != "null" ] && [ "$QUARTERLY_JOB_ID" != "" ]; then
        QUARTERLY_STATUS=$(curl -s "$API_URL/api/v1/predictions/jobs/$QUARTERLY_JOB_ID" \
          -H "Authorization: Bearer $ACCESS_TOKEN" | jq -r '.status' 2>/dev/null)
        echo "Quarterly Job Status: $QUARTERLY_STATUS"
    fi
    
    # Check if any job completed
    if [ "$ANNUAL_STATUS" = "completed" ] || [ "$QUARTERLY_STATUS" = "completed" ]; then
        echo "🎉 At least one job completed!"
        break
    elif [ "$ANNUAL_STATUS" = "failed" ] && [ "$QUARTERLY_STATUS" = "failed" ]; then
        echo "❌ Both jobs failed!"
        break
    fi
    
    sleep 5
done

echo
echo "5️⃣ Final Job Details:"
echo "====================="

if [ "$ANNUAL_JOB_ID" != "null" ] && [ "$ANNUAL_JOB_ID" != "" ]; then
    echo "Annual Job Final Status:"
    curl -s "$API_URL/api/v1/predictions/jobs/$ANNUAL_JOB_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN" | jq . 2>/dev/null
fi

if [ "$QUARTERLY_JOB_ID" != "null" ] && [ "$QUARTERLY_JOB_ID" != "" ]; then
    echo "Quarterly Job Final Status:"
    curl -s "$API_URL/api/v1/predictions/jobs/$QUARTERLY_JOB_ID" \
      -H "Authorization: Bearer $ACCESS_TOKEN" | jq . 2>/dev/null
fi

echo
echo "🔍 WORKER DIAGNOSTIC:"
echo "===================="
echo "• Check the worker monitoring terminal for job processing logs"
echo "• Jobs should show: 'Received task', 'Processing companies', 'Task completed'"
echo "• If no worker logs appear, the issue is job routing or task registration"
