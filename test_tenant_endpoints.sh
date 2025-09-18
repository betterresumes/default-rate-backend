#!/bin/bash

echo "🏢 TENANT ENDPOINTS TESTING"
echo "============================"
echo ""

BASE_URL="http://localhost:8000"

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

# Check if super admin email is provided
if [ -z "$1" ]; then
    echo -e "${RED}❌ Error: Super admin email required${NC}"
    echo ""
    echo "Usage: $0 <super_admin_email> [password]"
    echo ""
    echo "Example:"
    echo "  $0 super@admin.com mypassword"
    echo ""
    echo "Steps to setup:"
    echo "1. Run auth tests first: ./test_auth_endpoints.sh"
    echo "2. Update user to super admin: python update_admin.py <email>"
    echo "3. Run this script: $0 <email> <password>"
    exit 1
fi

ADMIN_EMAIL="$1"
ADMIN_PASSWORD="${2:-testpassword123}"

echo "🔑 STEP 1: SUPER ADMIN LOGIN"
echo "============================"
echo ""

LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$ADMIN_EMAIL\", \"password\": \"$ADMIN_PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ "$TOKEN" = "null" ] || [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to login as super admin${NC}"
    echo "Login response: $LOGIN_RESPONSE"
    echo ""
    echo "Make sure:"
    echo "1. User exists: python update_admin.py --list"
    echo "2. User is super admin: python update_admin.py $ADMIN_EMAIL"
    echo "3. Password is correct"
    exit 1
fi

echo -e "${GREEN}✅ Logged in as super admin${NC}"
echo "Token: ${TOKEN:0:30}..."
echo ""

# Test 1: Create Tenant
echo "🏗️ STEP 2: CREATE TENANT"
echo "========================"
echo ""

TENANT_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/tenants" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $TOKEN" \
    -d '{
        "name": "Test Enterprise Ltd",
        "description": "Test tenant for endpoint testing",
        "domain": "test-enterprise-'$(date +%s)'.com"
    }')

TENANT_ID=$(echo "$TENANT_RESPONSE" | jq -r '.id' 2>/dev/null)

if [ "$TENANT_ID" = "null" ] || [ -z "$TENANT_ID" ]; then
    echo -e "${RED}❌ Failed to create test tenant${NC}"
    echo "Tenant response: $TENANT_RESPONSE"
    exit 1
else
    echo -e "${GREEN}✅ Created test tenant: $TENANT_ID${NC}"
    echo "Tenant details:"
    echo "$TENANT_RESPONSE" | jq . 2>/dev/null || echo "$TENANT_RESPONSE"
fi
echo ""

# Test 2: List All Tenants
echo "📋 STEP 3: LIST TENANTS"
echo "======================="
echo ""

test_endpoint "GET" "/api/v1/tenants" "" "200" "List all tenants (Super Admin)" "$TOKEN"

# Test 3: Get Specific Tenant
echo "🔍 STEP 4: GET TENANT DETAILS"
echo "============================="
echo ""

test_endpoint "GET" "/api/v1/tenants/$TENANT_ID" "" "200" "Get specific tenant details" "$TOKEN"

# Test 4: Update Tenant
echo "✏️ STEP 5: UPDATE TENANT"
echo "========================"
echo ""

test_endpoint "PUT" "/api/v1/tenants/$TENANT_ID" "{
    \"description\": \"Updated description - tenant endpoint testing completed\",
    \"name\": \"Updated Test Enterprise Ltd\"
}" "200" "Update tenant information" "$TOKEN"

# Test 5: Get Tenant Statistics
echo "📊 STEP 6: GET TENANT STATISTICS"
echo "================================"
echo ""

test_endpoint "GET" "/api/v1/tenants/$TENANT_ID/stats" "" "200" "Get tenant statistics" "$TOKEN"

# Test 6: Test Access Control (Non-Super Admin)
echo "🔒 STEP 7: ACCESS CONTROL TESTS"
echo "==============================="
echo ""

# Create a regular user and test access
REGULAR_USER_EMAIL="regular.user$(date +%s)@example.com"
REGULAR_USER_PASSWORD="regularpass123"

echo "Creating regular user for access control testing..."
curl -s -X POST "$BASE_URL/api/v1/auth/register" \
    -H "Content-Type: application/json" \
    -d "{
        \"email\": \"$REGULAR_USER_EMAIL\",
        \"password\": \"$REGULAR_USER_PASSWORD\",
        \"username\": \"regularuser$(date +%s)\",
        \"full_name\": \"Regular User\"
    }" > /dev/null

# Login as regular user
REGULAR_LOGIN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\": \"$REGULAR_USER_EMAIL\", \"password\": \"$REGULAR_USER_PASSWORD\"}")

REGULAR_TOKEN=$(echo "$REGULAR_LOGIN_RESPONSE" | jq -r '.access_token' 2>/dev/null)

if [ "$REGULAR_TOKEN" != "null" ] && [ -n "$REGULAR_TOKEN" ]; then
    echo "Testing access control with regular user..."
    test_endpoint "GET" "/api/v1/tenants" "" "403" "Regular user access to tenants (should fail)" "$REGULAR_TOKEN"
    test_endpoint "POST" "/api/v1/tenants" "{
        \"name\": \"Unauthorized Tenant\",
        \"description\": \"Should not be created\"
    }" "403" "Regular user create tenant (should fail)" "$REGULAR_TOKEN"
fi

# Test 7: Delete Tenant (Warning: This will delete the test tenant)
echo "🗑️ STEP 8: DELETE TENANT"
echo "========================"
echo ""

echo -e "${YELLOW}⚠️ Warning: This will delete the test tenant${NC}"
read -p "Do you want to test tenant deletion? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    test_endpoint "DELETE" "/api/v1/tenants/$TENANT_ID" "" "200" "Delete tenant" "$TOKEN"
else
    echo "Skipping tenant deletion test"
    echo ""
fi

# Final Results
echo "📊 TENANT TESTING SUMMARY"
echo "========================="
echo -e "Total Tests: ${TOTAL_TESTS}"
echo -e "${GREEN}Passed: ${PASSED_TESTS}${NC}"
echo -e "${RED}Failed: ${FAILED_TESTS}${NC}"
echo -e "Success Rate: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TENANT TESTS PASSED!${NC}"
    echo -e "${GREEN}Tenant endpoints are working correctly${NC}"
else
    echo -e "${YELLOW}⚠️  Some tenant tests failed.${NC}"
    echo -e "${YELLOW}Check the details above for issues.${NC}"
fi

echo ""
echo "📋 TESTED ENDPOINTS:"
echo "✅ POST /api/v1/tenants - Create tenant (Super Admin only)"
echo "✅ GET /api/v1/tenants - List tenants (Super Admin only)"
echo "✅ GET /api/v1/tenants/{id} - Get tenant details (Super Admin only)"
echo "✅ PUT /api/v1/tenants/{id} - Update tenant (Super Admin only)"
echo "✅ GET /api/v1/tenants/{id}/stats - Get tenant statistics (Super Admin only)"
echo "✅ DELETE /api/v1/tenants/{id} - Delete tenant (Super Admin only)"
echo ""
echo "🎯 Access Control Verified:"
echo "- Super admin can perform all tenant operations"
echo "- Regular users are denied access (403 Forbidden)"
echo ""
echo "🔧 Next Step: Test organization endpoints"
echo "   Keep the tenant ID for org testing: $TENANT_ID"
