#!/bin/bash

# API Testing Guide - Multi-Tenant Financial Risk Prediction System
# Make sure the server is running on http://127.0.0.1:8000

echo "🚀 Testing Multi-Tenant Financial Risk API"
echo "=========================================="

# Step 1: Login to get JWT token
echo "Step 1: Login to get authentication token"
LOGIN_RESPONSE=$(curl -s -X POST "http://127.0.0.1:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }')

echo "Login Response: $LOGIN_RESPONSE"

# Extract token (you'll need to replace this with actual token from response)
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxOGU4YTU4Yy04NDdiLTRiMzUtOTMyMS1lYTA4Yzk3ZDE2NzMiLCJleHAiOjE3NTgyOTU5ODZ9.QwC2APnMqgiCPOZ5uvAa3IRgHPX-E6UNZH40K-hDQwQ"

echo ""
echo "Step 2: Test Annual Prediction Creation"
echo "======================================"
curl -X POST "http://127.0.0.1:8000/api/v1/predictions/annual" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_symbol": "AAPL",
    "company_name": "Apple Inc",
    "market_cap": 2800000,
    "sector": "Technology", 
    "reporting_year": "2023",
    "long_term_debt_to_total_capital": 0.15,
    "total_debt_to_ebitda": 2.5,
    "net_income_margin": 0.25,
    "ebit_to_interest_expense": 8.2,
    "return_on_assets": 0.18
  }' | jq '.'

echo ""
echo "Step 3: Test Quarterly Prediction Creation"
echo "========================================="
curl -X POST "http://127.0.0.1:8000/api/v1/predictions/quarterly" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_symbol": "TSLA",
    "company_name": "Tesla Inc",
    "market_cap": 800000,
    "sector": "Automotive",
    "reporting_year": "2023",
    "reporting_quarter": "Q1",
    "total_debt_to_ebitda": 3.1,
    "sga_margin": 0.24,
    "long_term_debt_to_total_capital": 0.12,
    "return_on_capital": 0.16
  }' | jq '.'

echo ""
echo "Step 4: List Annual Predictions"
echo "=============================="
curl -X GET "http://127.0.0.1:8000/api/v1/predictions/annual?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo ""
echo "Step 5: List Quarterly Predictions"
echo "================================="
curl -X GET "http://127.0.0.1:8000/api/v1/predictions/quarterly?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo ""
echo "Step 6: List Companies (created automatically)"
echo "============================================="
curl -X GET "http://127.0.0.1:8000/api/v1/companies/?page=1&size=10" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo ""
echo "Step 7: Test Bulk Upload (Create CSV first)"
echo "==========================================="
cat > test_annual_predictions.csv << EOF
company_symbol,company_name,market_cap,sector,reporting_year,long_term_debt_to_total_capital,total_debt_to_ebitda,net_income_margin,ebit_to_interest_expense,return_on_assets
MSFT,Microsoft Corp,2400000,Technology,2023,0.18,2.8,0.30,9.1,0.20
GOOGL,Alphabet Inc,1600000,Technology,2023,0.10,1.9,0.22,12.5,0.15
AMZN,Amazon Inc,1200000,E-commerce,2023,0.25,4.2,0.05,3.8,0.08
EOF

curl -X POST "http://127.0.0.1:8000/api/v1/predictions/bulk-upload?prediction_type=annual" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_annual_predictions.csv" | jq '.'

echo ""
echo "Step 8: Test Quarterly Bulk Upload"
echo "================================="
cat > test_quarterly_predictions.csv << EOF
company_symbol,company_name,market_cap,sector,reporting_year,reporting_quarter,total_debt_to_ebitda,sga_margin,long_term_debt_to_total_capital,return_on_capital
MSFT,Microsoft Corp,2400000,Technology,2023,Q2,2.8,0.20,0.18,0.25
GOOGL,Alphabet Inc,1600000,Technology,2023,Q2,1.9,0.15,0.10,0.28
AMZN,Amazon Inc,1200000,E-commerce,2023,Q2,4.2,0.32,0.25,0.12
EOF

curl -X POST "http://127.0.0.1:8000/api/v1/predictions/bulk-upload?prediction_type=quarterly" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test_quarterly_predictions.csv" | jq '.'

echo ""
echo "Step 9: Test Filtering - Get Apple predictions only"
echo "=================================================="
curl -X GET "http://127.0.0.1:8000/api/v1/predictions/annual?company_symbol=AAPL" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo ""
echo "Step 10: Test Year Filtering"
echo "==========================="
curl -X GET "http://127.0.0.1:8000/api/v1/predictions/annual?reporting_year=2023" \
  -H "Authorization: Bearer $TOKEN" | jq '.'

echo ""
echo "✅ Testing Complete!"
echo "==================="
echo "Check the responses above to verify:"
echo "1. Predictions are created successfully"
echo "2. Companies are auto-created during prediction"
echo "3. ML models return probability, risk_level, confidence"
echo "4. Access control works based on user role"
echo "5. Bulk upload processes multiple records"
echo "6. Filtering works properly"
