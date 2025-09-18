#!/bin/bash

# Test script to verify user registration error handling

BASE_URL="http://localhost:8000"

echo "🧪 Testing User Registration Error Handling"
echo "============================================="

echo
echo "1. Testing duplicate username (explicit)..."
curl -X POST "${BASE_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test1@example.com",
    "password": "TestPassword123!",
    "first_name": "Test",
    "last_name": "User",
    "username": "admin"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.' 2>/dev/null || cat

echo
echo "2. Testing auto-generated username collision..."
curl -X POST "${BASE_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@newcompany.com",
    "password": "TestPassword123!",
    "first_name": "Admin",
    "last_name": "User"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.' 2>/dev/null || cat

echo
echo "3. Testing successful registration with unique email..."
curl -X POST "${BASE_URL}/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "unique.user@example.com",
    "password": "TestPassword123!",
    "first_name": "Unique",
    "last_name": "User"
  }' \
  -w "\nHTTP Status: %{http_code}\n" \
  -s | jq '.' 2>/dev/null || cat

echo
echo "✅ Test completed!"
