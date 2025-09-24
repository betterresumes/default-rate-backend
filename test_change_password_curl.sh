#!/bin/bash

# Test Change Password API
# Make sure your server is running on localhost:8000

BASE_URL="http://localhost:8000/api/v1"

echo "🔐 Testing Change Password API"
echo "================================"

echo ""
echo "📝 First, you need to login to get a token:"
echo "curl -X POST \"${BASE_URL}/auth/login\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"email\": \"your-email@example.com\", \"password\": \"your-current-password\"}'"

echo ""
echo "💡 Copy the access_token from the login response, then test change password:"

echo ""
echo "🔄 Test 1: Valid password change"
echo "curl -X POST \"${BASE_URL}/auth/change-password\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -H \"Authorization: Bearer YOUR_JWT_TOKEN\" \\"
echo "     -d '{\"current_password\": \"your-current-password\", \"new_password\": \"your-new-password123\"}'"

echo ""
echo "❌ Test 2: Wrong current password"
echo "curl -X POST \"${BASE_URL}/auth/change-password\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -H \"Authorization: Bearer YOUR_JWT_TOKEN\" \\"
echo "     -d '{\"current_password\": \"wrong-password\", \"new_password\": \"new-password123\"}'"

echo ""
echo "🚫 Test 3: Weak new password"
echo "curl -X POST \"${BASE_URL}/auth/change-password\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -H \"Authorization: Bearer YOUR_JWT_TOKEN\" \\"
echo "     -d '{\"current_password\": \"your-current-password\", \"new_password\": \"weak\"}'"

echo ""
echo "🔒 Test 4: No authentication"
echo "curl -X POST \"${BASE_URL}/auth/change-password\" \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"current_password\": \"your-current-password\", \"new_password\": \"new-password123\"}'"

echo ""
echo "✅ Expected Responses:"
echo "   Success (200): {\"success\": true, \"message\": \"Password changed successfully\"}"
echo "   Error (400): {\"detail\": \"Current password is incorrect\"}"
echo "   Error (422): {\"detail\": [validation error details]}"
echo "   Error (401): {\"detail\": \"Not authenticated\"}"

echo ""
echo "🎯 API Endpoint: POST ${BASE_URL}/auth/change-password"
echo "🔐 Requires: Valid JWT token in Authorization header"
echo "📋 Body: {\"current_password\": \"string\", \"new_password\": \"string\"}"
