#!/bin/bash

# Dashboard API Test - Morgan Stanley Risk Director
# This script logs in and tests the new POST /dashboard endpoint

BASE_URL="http://localhost:8000"
LOGIN_URL="$BASE_URL/api/v1/auth/login"
DASHBOARD_URL="$BASE_URL/api/v1/predictions/dashboard"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Dashboard API Test - Morgan Stanley Risk Director${NC}"
echo "=================================================================="

# Step 1: Login to get JWT token
echo -e "\n${YELLOW}🔐 Step 1: Logging in...${NC}"
echo "📧 Email: risk.director@morganstanley.com"

LOGIN_RESPONSE=$(curl -s -X POST "$LOGIN_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "risk.director@morganstanley.com",
    "password": "Director123!"
  }')

echo "📊 Login Response:"
echo "$LOGIN_RESPONSE" | jq . 2>/dev/null || echo "$LOGIN_RESPONSE"

# Extract token from response
TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token // .token // .jwt // .bearer // empty' 2>/dev/null)

if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
    echo -e "${RED}❌ Failed to get token from login response${NC}"
    echo "💡 Make sure:"
    echo "   1. FastAPI server is running on localhost:8000"
    echo "   2. You ran: python scripts/setup_realistic_users.py"
    echo "   3. Database is accessible"
    exit 1
fi

echo -e "${GREEN}✅ Login successful!${NC}"
echo "🎫 Token: ${TOKEN:0:30}..."

# Step 2: Test Dashboard with Platform Stats
echo -e "\n${YELLOW}📈 Step 2: Testing Dashboard with Platform Stats...${NC}"

DASHBOARD_RESPONSE=$(curl -s -X POST "$DASHBOARD_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "include_platform_stats": true,
    "custom_scope": "organization"
  }')

echo "📊 Dashboard Response:"
echo "$DASHBOARD_RESPONSE" | jq . 2>/dev/null || echo "$DASHBOARD_RESPONSE"

# Check if response is successful
if echo "$DASHBOARD_RESPONSE" | jq -e '.scope' >/dev/null 2>&1; then
    echo -e "${GREEN}✅ Dashboard endpoint working successfully!${NC}"
    
    # Extract key metrics
    SCOPE=$(echo "$DASHBOARD_RESPONSE" | jq -r '.scope // "unknown"')
    USER_NAME=$(echo "$DASHBOARD_RESPONSE" | jq -r '.user_name // "unknown"')
    TOTAL_COMPANIES=$(echo "$DASHBOARD_RESPONSE" | jq -r '.total_companies // 0')
    TOTAL_PREDICTIONS=$(echo "$DASHBOARD_RESPONSE" | jq -r '.total_predictions // 0')
    PLATFORM_PREDICTIONS=$(echo "$DASHBOARD_RESPONSE" | jq -r '.platform_statistics.total_predictions // "N/A"')
    
    echo -e "\n${BLUE}📋 Dashboard Summary:${NC}"
    echo "   🎯 Scope: $SCOPE"
    echo "   👤 User: $USER_NAME"
    echo "   🏢 User's Companies: $TOTAL_COMPANIES"
    echo "   📊 User's Predictions: $TOTAL_PREDICTIONS"
    echo "   🌐 Platform Total Predictions: $PLATFORM_PREDICTIONS"
else
    echo -e "${RED}❌ Dashboard request failed${NC}"
fi

# Step 3: Test Dashboard without Platform Stats
echo -e "\n${YELLOW}📈 Step 3: Testing Dashboard without Platform Stats...${NC}"

DASHBOARD_RESPONSE_2=$(curl -s -X POST "$DASHBOARD_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "include_platform_stats": false,
    "custom_scope": "personal"
  }')

echo "📊 Personal Dashboard Response:"
echo "$DASHBOARD_RESPONSE_2" | jq . 2>/dev/null || echo "$DASHBOARD_RESPONSE_2"

# Step 4: Test Dashboard with System Scope (if permitted)
echo -e "\n${YELLOW}📈 Step 4: Testing System Scope (if permitted)...${NC}"

DASHBOARD_RESPONSE_3=$(curl -s -X POST "$DASHBOARD_URL" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "include_platform_stats": true,
    "custom_scope": "system"
  }')

echo "📊 System Scope Response:"
echo "$DASHBOARD_RESPONSE_3" | jq . 2>/dev/null || echo "$DASHBOARD_RESPONSE_3"

echo -e "\n${GREEN}🏁 Testing completed!${NC}"
echo "=================================================================="
