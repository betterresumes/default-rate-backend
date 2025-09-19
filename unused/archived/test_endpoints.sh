#!/bin/bash

# Test script for new prediction endpoints
# Token provided by user
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI3ZWJlOWZjNS0wMThlLTRlNDUtYWVmYS1iMDlhMWUwNjc0ZTAiLCJleHAiOjE3NTc3ODkwOTB9.pw_CdSiRxh-EN1dHoLkdc705PRyHJSeWz03vs9tMX2I"
BASE_URL="http://localhost:8000"

echo "======================================"
echo "Testing New Prediction Endpoints"
echo "======================================"

# Using existing company IDs from the list
COMPANY_ID="9e8cbecc-f800-47dd-88a4-c8f25f25e264"  # CONSUMER company
COMPANY_ID_2="992cb72e-94bb-407e-85a0-bfda28645441"  # TECHCO company

echo ""
echo "1. Testing Update Prediction Endpoint (Company Info Only)"
echo "------------------------------------------------------"
curl -X PUT "${BASE_URL}/api/predictions/update/${COMPANY_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Updated Consumer Goods Corp",
    "sector": "Updated Consumer Sector",
    "market_cap": 15000.0,
    "reporting_year": "2025",
    "reporting_quarter": "Q3"
  }' | jq .

echo ""
echo "2. Testing Update Prediction Endpoint (With Financial Ratios - Should Recalculate)"
echo "---------------------------------------------------------------------------------"
curl -X PUT "${BASE_URL}/api/predictions/update/${COMPANY_ID}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Consumer Goods with New Ratios",
    "long_term_debt_to_total_capital": 28.5,
    "net_income_margin": 16.8,
    "return_on_assets": 12.3
  }' | jq .

echo ""
echo "3. Testing Update Prediction Endpoint (Partial Ratio Update)"
echo "------------------------------------------------------------"
curl -X PUT "${BASE_URL}/api/predictions/update/${COMPANY_ID_2}" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "total_debt_to_ebitda": 1.8,
    "ebit_to_interest_expense": 20.5
  }' | jq .

echo ""
echo "4. Testing Update Prediction Endpoint (Invalid Company ID)"
echo "----------------------------------------------------------"
curl -X PUT "${BASE_URL}/api/predictions/update/invalid-company-id" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "This should fail"
  }' | jq .

echo ""
echo "5. Testing Delete Company Endpoint"
echo "-----------------------------------"
# Let's create a test company first, then delete it
echo "Creating a test company to delete..."
curl -X POST "${BASE_URL}/api/predictions/predict-default-rate" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "stock_symbol": "TESTDEL",
    "company_name": "Test Delete Company",
    "market_cap": 1000000000.0,
    "sector": "Test Sector",
    "reporting_year": "2024",
    "reporting_quarter": "Q4",
    "long_term_debt_to_total_capital": 30.0,
    "total_debt_to_ebitda": 3.0,
    "net_income_margin": 15.0,
    "ebit_to_interest_expense": 8.0,
    "return_on_assets": 10.0
  }' | jq .

echo ""
echo "Getting the test company ID to delete..."
RESPONSE=$(curl -s -X GET "${BASE_URL}/api/companies/" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json")

TEST_COMPANY_ID=$(echo $RESPONSE | jq -r '.data.companies[] | select(.symbol=="TESTDEL") | .id')

if [ "$TEST_COMPANY_ID" != "null" ] && [ -n "$TEST_COMPANY_ID" ]; then
    echo "Found test company ID: $TEST_COMPANY_ID"
    echo "Now deleting the test company..."
    curl -X DELETE "${BASE_URL}/api/predictions/delete/${TEST_COMPANY_ID}" \
      -H "Authorization: Bearer ${TOKEN}" | jq .
else
    echo "Could not find test company to delete"
fi

echo ""
echo "6. Testing Delete Non-Existent Company"
echo "--------------------------------------"
curl -X DELETE "${BASE_URL}/api/predictions/delete/non-existent-id" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

echo ""
echo "7. Testing Admin Reset Database (Without Confirmation - Should Fail)"
echo "--------------------------------------------------------------------"
curl -X POST "${BASE_URL}/api/predictions/admin/reset-database" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "companies",
    "confirm_reset": false
  }' | jq .

echo ""
echo "8. Testing Admin Reset Database (Non-Admin User - Should Fail)"
echo "--------------------------------------------------------------"
# This should fail since the user might not be admin
curl -X POST "${BASE_URL}/api/predictions/admin/reset-database" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "table_name": "companies",
    "confirm_reset": true
  }' | jq .

echo ""
echo "9. Testing Auth User Info (to check admin status)"
echo "-------------------------------------------------"
curl -X GET "${BASE_URL}/api/auth/me" \
  -H "Authorization: Bearer ${TOKEN}" | jq .

echo ""
echo "======================================"
echo "Testing Complete!"
echo "======================================"
