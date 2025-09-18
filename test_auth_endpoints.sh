#!/bin/bash

echo "🔐 AUTHENTICATION ENDPOINTS TESTING"
echo "==================================="
echo ""

BASE_URL="http://localhost:8000"
TEST_EMAIL="auth.test@example.com"
TEST_PASSWORD="testpassword123"

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

# Test 1: User Registration (Public)
echo "📝 STEP 1: USER REGISTRATION"
echo "============================"
echo ""

test_endpoint "POST" "/api/v1/auth/register" "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"username\": \"authtest$(date +%s)\",
    \"full_name\": \"Auth Test User\"
}" "201" "Register new user (public)"

# Test 2: User Login
echo "🔑 STEP 2: USER LOGIN"
echo "===================="
echo ""

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$TEST_EMAIL\", \"password\": \"$TEST_PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token' 2>/dev/null)

echo "Login Response:"
echo "$LOGIN_RESPONSE" | jq . 2>/dev/null || echo "$LOGIN_RESPONSE"

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to get authentication token${NC}"
    echo "Login response: $LOGIN_RESPONSE"
    exit 1
fi

echo -e "${GREEN}✅ Got authentication token: ${TOKEN:0:30}...${NC}"
echo ""

# Test 3: Token Refresh
echo "🔄 STEP 3: TOKEN REFRESH"
echo "========================"
echo ""

test_endpoint "POST" "/api/v1/auth/refresh" "" "200" "Refresh JWT token" "$TOKEN"

# Test 4: Test Join Organization Endpoint (should require token)
echo "🤝 STEP 4: JOIN ORGANIZATION"
echo "=========================="
echo ""

test_endpoint "POST" "/api/v1/auth/join" "{
    \"token\": \"dummy-join-token\"
}" "400" "Join organization with invalid token"

# Test 5: User Logout
echo "🚪 STEP 5: USER LOGOUT"
echo "======================"
echo ""

test_endpoint "POST" "/api/v1/auth/logout" "" "200" "Logout user" "$TOKEN"

# Test 6: Test Token After Logout (should fail)
echo "🔒 STEP 6: VERIFY TOKEN INVALIDATION"
echo "==================================="
echo ""

test_endpoint "POST" "/api/v1/auth/refresh" "" "401" "Try refresh with logged out token" "$TOKEN"

# Test 7: Login with Wrong Credentials
echo "❌ STEP 7: INVALID LOGIN ATTEMPTS"
echo "================================="
echo ""

test_endpoint "POST" "/api/v1/auth/login" "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"wrongpassword\"
}" "401" "Login with wrong password"

test_endpoint "POST" "/api/v1/auth/login" "{
    \"email\": \"nonexistent@example.com\",
    \"password\": \"$TEST_PASSWORD\"
}" "401" "Login with non-existent email"

# Test 8: Register Duplicate User
echo "🔄 STEP 8: DUPLICATE REGISTRATION"
echo "================================="
echo ""

test_endpoint "POST" "/api/v1/auth/register" "{
    \"email\": \"$TEST_EMAIL\",
    \"password\": \"$TEST_PASSWORD\",
    \"username\": \"duplicate$(date +%s)\",
    \"full_name\": \"Duplicate User\"
}" "400" "Register with existing email (should fail)"

# Final Results
echo "📊 AUTHENTICATION TESTING SUMMARY"
echo "=================================="
echo -e "Total Tests: ${TOTAL_TESTS}"
echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"
echo -e "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL AUTHENTICATION TESTS PASSED!${NC}"
    echo -e "${GREEN}Auth endpoints are working correctly${NC}"
else
    echo -e "${YELLOW}⚠️  Some authentication tests failed.${NC}"
    echo -e "${YELLOW}Check the details above for issues.${NC}"
fi

echo ""
echo "📋 TESTED ENDPOINTS:"
echo "✅ POST /api/v1/auth/register - User registration"
echo "✅ POST /api/v1/auth/login - User login"
echo "✅ POST /api/v1/auth/refresh - Token refresh"
echo "✅ POST /api/v1/auth/join - Join organization"
echo "✅ POST /api/v1/auth/logout - User logout"
echo ""
echo "🔧 Next Step: Update user to super admin for tenant testing:"
echo "   python update_admin.py $TEST_EMAIL"
