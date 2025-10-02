#!/bin/bash

# Fix CloudFront CORS - Allow All HTTP Methods
set -e
export AWS_DEFAULT_REGION=us-east-1

echo "🔧 Fixing CloudFront CORS Configuration"
echo "======================================="
echo "Issue: CloudFront only allows GET/HEAD, but CORS needs OPTIONS, POST, PUT, DELETE"
echo

DISTRIBUTION_ID="E22V6U663GQWNO"

# Get current distribution config
echo "📥 Getting current CloudFront configuration..."
CURRENT_CONFIG=$(aws cloudfront get-distribution-config --id $DISTRIBUTION_ID)
ETAG=$(echo "$CURRENT_CONFIG" | jq -r '.ETag')

echo "Current ETag: $ETAG"

# Extract and modify the distribution config
echo "🔄 Updating configuration to allow all HTTP methods..."
echo "$CURRENT_CONFIG" | jq '.DistributionConfig | 
.DefaultCacheBehavior.AllowedMethods = {
  "Quantity": 7,
  "Items": ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"],
  "CachedMethods": {
    "Quantity": 2, 
    "Items": ["GET", "HEAD"]
  }
} |
.DefaultCacheBehavior.ForwardedValues.Headers = {
  "Quantity": 8,
  "Items": ["Authorization", "Origin", "Accept", "Content-Type", "Access-Control-Request-Method", "Access-Control-Request-Headers", "Host", "User-Agent"]
} |
.DefaultCacheBehavior.MinTTL = 0 |
.DefaultCacheBehavior.DefaultTTL = 0 |
.DefaultCacheBehavior.MaxTTL = 86400' > /tmp/fixed-config.json

echo "📋 Updated Configuration Preview:"
echo "================================"
echo "Allowed Methods: DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
echo "Cached Methods: GET, HEAD (only)"
echo "Forwarded Headers: Authorization, Origin, Accept, Content-Type, Access-Control-Request-Method, Access-Control-Request-Headers, Host, User-Agent"
echo "TTL: Min=0, Default=0, Max=24h"

# Apply the updated configuration
echo -e "\n🚀 Applying CloudFront configuration update..."
UPDATE_RESULT=$(aws cloudfront update-distribution \
  --id $DISTRIBUTION_ID \
  --distribution-config file:///tmp/fixed-config.json \
  --if-match "$ETAG")

NEW_STATUS=$(echo "$UPDATE_RESULT" | jq -r '.Distribution.Status')
echo "✅ CloudFront update initiated!"
echo "Status: $NEW_STATUS"

# Clean up
rm -f /tmp/fixed-config.json

echo -e "\n⏳ IMPORTANT: CloudFront Update Timeline"
echo "========================================"
echo "• Update Status: InProgress"
echo "• Deployment Time: 5-15 minutes"
echo "• Global Edge Cache: May take up to 24 hours for full propagation"
echo ""
echo "🧪 Testing CORS:"
echo "==============="
echo "Wait 5-10 minutes, then test:"
echo "curl -X OPTIONS https://d3tytmnn6rkqkb.cloudfront.net/api/v1/auth/register \\"
echo "  -H 'Origin: https://your-frontend-domain.com' \\"
echo "  -H 'Access-Control-Request-Method: POST' \\"
echo "  -H 'Access-Control-Request-Headers: Content-Type,Authorization' \\"
echo "  -v"
echo ""
echo "🎯 What Was Fixed:"
echo "=================="
echo "❌ Before: Only GET, HEAD allowed"
echo "✅ After:  All HTTP methods allowed (DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT)"
echo "❌ Before: Limited headers forwarded"  
echo "✅ After:  CORS headers properly forwarded"
echo "❌ Before: High TTL caused caching issues"
echo "✅ After:  Low TTL for dynamic API responses"
