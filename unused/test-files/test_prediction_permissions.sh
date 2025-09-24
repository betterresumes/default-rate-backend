#!/bin/bash

# Simple test script for prediction permissions
# Usage: ./test_prediction_permissions.sh <JWT_TOKEN>

PREDICTION_ID="47697e2c-60ce-4ddf-901f-00a3f3fa5e8b"
BASE_URL="http://localhost:8000/api/v1"
TOKEN="$1"

if [ -z "$TOKEN" ]; then
    echo "❌ Usage: $0 <JWT_TOKEN>"
    echo "   Get your token from login API first"
    exit 1
fi

echo "🚀 Testing Prediction Permissions"
echo "=================================="
echo "📋 Prediction ID: $PREDICTION_ID"
echo ""

# Test 1: Get prediction details
echo "1️⃣ Testing GET permission (view prediction)..."
curl -s -H "Authorization: Bearer $TOKEN" \
     "$BASE_URL/predictions/annual?page=1&size=100" \
     | grep -q "$PREDICTION_ID"

if [ $? -eq 0 ]; then
    echo "✅ FOUND - User can view this prediction"
else
    echo "❌ NOT FOUND - User cannot view this prediction"
    echo "   This might be a system-level prediction or doesn't exist"
fi

echo ""

# Test 2: Test UPDATE permission
echo "2️⃣ Testing PUT permission (update prediction)..."
UPDATE_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/update_response.json \
    -X PUT \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "company_name": "Test Update Company",
        "company_symbol": "TUPDT",
        "market_cap": 1500000000,
        "sector": "Technology",
        "reporting_year": "2024",
        "reporting_quarter": null,
        "long_term_debt_to_total_capital": 0.25,
        "total_debt_to_ebitda": 1.5,
        "net_income_margin": 0.15,
        "ebit_to_interest_expense": 12.0,
        "return_on_assets": 0.08
    }' \
    "$BASE_URL/predictions/annual/$PREDICTION_ID")

echo "📊 HTTP Status: $UPDATE_RESPONSE"

if [ "$UPDATE_RESPONSE" = "200" ]; then
    echo "✅ UPDATE SUCCESSFUL - User can update this prediction!"
    echo "📝 Response:"
    cat /tmp/update_response.json | python3 -m json.tool 2>/dev/null || cat /tmp/update_response.json
else
    echo "❌ UPDATE FAILED"
    echo "📝 Error response:"
    cat /tmp/update_response.json | python3 -m json.tool 2>/dev/null || cat /tmp/update_response.json
fi

echo ""

# Test 3: Test DELETE permission (commented out to prevent accidental deletion)
echo "3️⃣ Testing DELETE permission..."
echo "⚠️  DELETE test is DISABLED to prevent accidental deletion"
echo "   Uncomment the lines below to test actual deletion"

# DELETE_RESPONSE=$(curl -s -w "%{http_code}" -o /tmp/delete_response.json \
#     -X DELETE \
#     -H "Authorization: Bearer $TOKEN" \
#     "$BASE_URL/predictions/annual/$PREDICTION_ID")
# 
# echo "📊 HTTP Status: $DELETE_RESPONSE"
# 
# if [ "$DELETE_RESPONSE" = "200" ]; then
#     echo "✅ DELETE SUCCESSFUL - User can delete this prediction!"
# else
#     echo "❌ DELETE FAILED"
#     echo "📝 Error response:"
#     cat /tmp/delete_response.json | python3 -m json.tool 2>/dev/null || cat /tmp/delete_response.json
# fi

echo ""
echo "🏁 Test completed!"
echo ""
echo "💡 To debug further:"
echo "   1. Check the server logs for detailed error messages"
echo "   2. Verify the JWT token is valid and not expired"
echo "   3. Check if the prediction exists and user has correct permissions"
echo "   4. Use: python3 debug_prediction_permissions.py"
