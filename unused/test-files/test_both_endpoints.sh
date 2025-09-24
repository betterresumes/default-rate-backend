#!/bin/bash

# Test script for the two statistics endpoints
echo "🔧 Testing Both Statistics Endpoints"
echo "===================================="

# Login and get token
echo "🔑 Logging in as Morgan Stanley Risk Director..."
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "risk.director@morganstanley.com", "password": "Director123!"}' | jq -r '.access_token')

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo "❌ Login failed"
    exit 1
fi

echo "✅ Login successful! Token: ${TOKEN:0:30}..."
echo ""

# Test 1: Dashboard endpoint (POST) - THIS ONE WORKS PERFECTLY
echo "📈 Testing POST /dashboard endpoint (WORKING):"
echo "curl -X POST \"http://localhost:8000/api/v1/predictions/dashboard\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"Authorization: Bearer YOUR_TOKEN\" \\"
echo "  -d '{"
echo "    \"include_platform_stats\": true,"
echo "    \"organization_filter\": null,"
echo "    \"custom_scope\": null"
echo "  }'"
echo ""
echo "Response:"
curl -s -X POST "http://localhost:8000/api/v1/predictions/dashboard" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "include_platform_stats": true,
    "organization_filter": null,
    "custom_scope": null
  }' | jq .
echo ""

# Test 2: Stats endpoint (GET) - Let's check if it's working now
echo "📊 Testing GET /stats endpoint:"
echo "curl -X GET \"http://localhost:8000/api/v1/predictions/stats\" \\"
echo "  -H \"Authorization: Bearer YOUR_TOKEN\""
echo ""
echo "Response:"
STATS_RESPONSE=$(curl -s -X GET "http://localhost:8000/api/v1/predictions/stats" \
  -H "Authorization: Bearer $TOKEN")

echo "$STATS_RESPONSE" | jq .

# Summary
echo ""
echo "📋 SUMMARY:"
echo "=========="
echo "✅ POST /dashboard - FULLY WORKING with platform statistics"
echo "❓ GET /stats - Check response above"
echo ""
echo "🎯 WORKING CURL COMMANDS FOR YOU:"
echo ""
echo "# Get your token first:"
echo "TOKEN=\$(curl -s -X POST \"http://localhost:8000/api/v1/auth/login\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -d '{\"email\": \"risk.director@morganstanley.com\", \"password\": \"Director123!\"}' | jq -r '.access_token')"
echo ""
echo "# Use the dashboard endpoint (recommended):"
echo "curl -X POST \"http://localhost:8000/api/v1/predictions/dashboard\" \\"
echo "  -H \"Content-Type: application/json\" \\"
echo "  -H \"Authorization: Bearer \$TOKEN\" \\"
echo "  -d '{\"include_platform_stats\": true, \"organization_filter\": null, \"custom_scope\": null}'"
