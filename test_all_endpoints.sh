#!/bin/bash

echo "🎯 COMPREHENSIVE API ENDPOINT TESTING"
echo "======================================"
echo ""

BASE_URL="http://localhost:8000"
TEST_EMAIL="test.super$(date +%s)@admin.com"
TEST_PASSWORD="testadmin123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5
    local token=$6
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${BLUE}Testing: ${method} ${endpoint}${NC}"
    echo "Description: ${description}"
    
    if [ -n "$token" ]; then
        auth_header="-H \"Authorization: Bearer $token\""
    else
        auth_header=""
    fi
    
    if [ -n "$data" ]; then
        data_param="-d '$data'"
    else
        data_param=""
    fi
    
    response=$(eval "curl -s -w 'HTTP_STATUS:%{http_code}' -X $method '$BASE_URL$endpoint' -H 'Content-Type: application/json' $auth_header $data_param")
    
    # Extract HTTP status
    http_status=$(echo "$response" | grep -o 'HTTP_STATUS:[0-9]*' | cut -d: -f2)
    response_body=$(echo "$response" | sed 's/HTTP_STATUS:[0-9]*$//')
    
    if [ "$http_status" = "$expected_status" ]; then
        echo -e "${GREEN}✅ PASSED (${http_status})${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        if [ -n "$response_body" ] && [ "$response_body" != "{}" ]; then
            echo "$response_body" | jq . 2>/dev/null || echo "$response_body"
        fi
    else
        echo -e "${RED}❌ FAILED (Expected: ${expected_status}, Got: ${http_status})${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "Response: $response_body"
    fi
    echo ""
}

# Step 1: Register Super Admin
echo "🔐 STEP 1: AUTHENTICATION SETUP"
echo "================================"
echo ""

test_endpoint "POST" "/api/v1/auth/register" "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"username\": \"testsuperadmin$(date +%s)\",
    \"first_name\": \"Test\",
    \"last_name\": \"Admin\",
    \"global_role\": \"super_admin\"
}" "201" "Register super admin"

# Step 2: Login and get token
echo "Getting authentication token..."
LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to get authentication token${NC}"
    echo "Login response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Got authentication token${NC}"
echo ""

# Step 3: Test Auth Endpoints
echo "🔐 STEP 2: AUTHENTICATION ENDPOINTS"
echo "==================================="
echo ""

test_endpoint "POST" "/api/v1/auth/refresh" "" "200" "Refresh JWT token" "$TOKEN"
test_endpoint "POST" "/api/v1/auth/logout" "" "200" "Logout user" "$TOKEN"

# Step 4: Create Test Tenant
echo "🏢 STEP 3: TENANT ENDPOINTS"
echo "=========================="
echo ""

TENANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/tenants" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "name": "Test Enterprise Corp",
        "description": "Test tenant for API testing",
        "domain": "test-enterprise-api.com"
    }')

TENANT_ID=$(echo "$TENANT_RESPONSE" | jq -r '.id' 2>/dev/null)

if [ "$TENANT_ID" = "null" ] || [ -z "$TENANT_ID" ]; then
    echo -e "${RED}❌ Failed to create test tenant${NC}"
    echo "Tenant response: $TENANT_RESPONSE"
else
    echo -e "${GREEN}✅ Created test tenant: $TENANT_ID${NC}"
fi

# Test tenant endpoints
test_endpoint "GET" "/api/v1/tenants/$TENANT_ID" "" "200" "Get tenant details" "$TOKEN"
test_endpoint "PUT" "/api/v1/tenants/$TENANT_ID" "{
    \"description\": \"Updated description for testing\"
}" "200" "Update tenant" "$TOKEN"
test_endpoint "GET" "/api/v1/tenants/$TENANT_ID/stats" "" "200" "Get tenant statistics" "$TOKEN"

# Step 5: Test Organization Endpoints
echo "🏛️ STEP 4: ORGANIZATION ENDPOINTS"
echo "================================="
echo ""

ORG_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/organizations" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "name": "Test Organization",
        "description": "Test org for API testing",
        "domain": "test-org-api.com",
        "tenant_id": "'$TENANT_ID'"
    }')

ORG_ID=$(echo "$ORG_RESPONSE" | jq -r '.id' 2>/dev/null)

if [ "$ORG_ID" = "null" ] || [ -z "$ORG_ID" ]; then
    echo -e "${RED}❌ Failed to create test organization${NC}"
    echo "Organization response: $ORG_RESPONSE"
else
    echo -e "${GREEN}✅ Created test organization: $ORG_ID${NC}"
fi

test_endpoint "GET" "/api/v1/organizations" "" "200" "List organizations" "$TOKEN"
test_endpoint "GET" "/api/v1/organizations/$ORG_ID" "" "200" "Get organization details" "$TOKEN"
test_endpoint "PUT" "/api/v1/organizations/$ORG_ID" "{
    \"description\": \"Updated org description\"
}" "200" "Update organization" "$TOKEN"
test_endpoint "GET" "/api/v1/organizations/$ORG_ID/users" "" "200" "Get organization users" "$TOKEN"
test_endpoint "GET" "/api/v1/organizations/$ORG_ID/whitelist" "" "200" "Get organization whitelist" "$TOKEN"

# Final Results
echo "📊 TESTING SUMMARY"
echo "=================="
echo -e "Total Tests: ${TOTAL_TESTS}"
echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"
echo -e "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED!${NC}"
else
    echo -e "${YELLOW}⚠️  Some tests failed. Check the details above.${NC}"
fi
