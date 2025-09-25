#!/bin/bash

# Test script for Railway deployment
# Replace YOUR_RAILWAY_URL with your actual Railway app URL

RAILWAY_URL="default-rate-backend-production.up.railway.app"

echo "🧪 Testing Railway deployment..."

echo "1. Testing health endpoint..."
curl -s "$RAILWAY_URL/health" | jq . || echo "Health endpoint test failed"

echo -e "\n2. Testing docs endpoint..."
curl -s -o /dev/null -w "%{http_code}" "$RAILWAY_URL/docs"
echo " - Docs endpoint status"

echo -e "\n3. Testing API v1 endpoints..."
curl -s "$RAILWAY_URL/api/v1/" | jq . || echo "API v1 test failed"

echo -e "\n✅ Replace 'your-app-name-production.up.railway.app' with your actual Railway URL and run this script"
  