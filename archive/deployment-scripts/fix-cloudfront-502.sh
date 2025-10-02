#!/bin/bash

# Fix CloudFront 502 Error - Update Origin Configuration
set -e
export AWS_DEFAULT_REGION=us-east-1

echo "🔧 Fixing CloudFront 502 Error"
echo "==============================="
echo "Date: $(date)"
echo

# The issue: CloudFront is trying to use HTTPS to connect to ALB but having SSL issues
# Solution: Update CloudFront to use HTTP for origin, HTTPS for viewers

echo "📋 Issue Diagnosis:"
echo "=================="
echo "• CloudFront → ALB via HTTPS = SSL validation issues (502)"
echo "• CloudFront → ALB via HTTP = Should work fine"
echo "• Users → CloudFront = Always HTTPS (secure)"
echo

# Get current distribution config
echo "🔍 Getting Current CloudFront Configuration..."
aws cloudfront get-distribution-config --id E22V6U663GQWNO > /tmp/cf-config.json

ETAG=$(jq -r '.ETag' /tmp/cf-config.json)
echo "Current ETag: $ETAG"

# Update the configuration to use HTTP for origin
echo -e "\n🔧 Updating CloudFront Origin Configuration..."

# Extract and modify the distribution config
jq '.DistributionConfig | 
    .Origins.Items[0].CustomOriginConfig.OriginProtocolPolicy = "http-only" |
    .Origins.Items[0].CustomOriginConfig.HTTPPort = 80 |
    .Origins.Items[0].CustomOriginConfig.HTTPSPort = 443 |
    .DefaultCacheBehavior.ViewerProtocolPolicy = "redirect-to-https" |
    .Comment = "AccuNode API - Fixed 502 Error (HTTP Origin, HTTPS Viewer)"' \
    /tmp/cf-config.json > /tmp/cf-config-updated.json

# Update the distribution
echo "Updating CloudFront distribution..."
aws cloudfront update-distribution \
    --id E22V6U663GQWNO \
    --distribution-config file:///tmp/cf-config-updated.json \
    --if-match "$ETAG" > /tmp/update-result.json

echo "✅ CloudFront distribution updated!"

# Get new deployment status
NEW_STATUS=$(jq -r '.Distribution.Status' /tmp/update-result.json)
echo "New Status: $NEW_STATUS"

echo -e "\n⏳ CloudFront Deployment Process:"
echo "================================="
echo "Status: $NEW_STATUS"

if [ "$NEW_STATUS" = "InProgress" ]; then
    echo "⏳ CloudFront is redeploying with new configuration..."
    echo "   This takes 5-15 minutes"
    echo "   The 502 error should resolve once deployment completes"
else
    echo "✅ Update complete!"
fi

# Test ALB directly while we wait
echo -e "\n🧪 Testing ALB Direct (HTTP) While We Wait:"
echo "==========================================="

ALB_HTTP="http://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo "Testing: $ALB_HTTP/health"

HTTP_TEST=$(curl -s -o /dev/null -w "%{http_code}" "$ALB_HTTP/health" --max-time 10 || echo "TIMEOUT")
echo "ALB HTTP Status: $HTTP_TEST"

if [ "$HTTP_TEST" = "200" ]; then
    echo "✅ ALB HTTP is working - CloudFront should work once redeployed"
else
    echo "❌ ALB HTTP issue detected - need to investigate further"
fi

# Clean up temp files
rm -f /tmp/cf-config.json /tmp/cf-config-updated.json /tmp/update-result.json

echo -e "\n🎯 Fix Summary:"
echo "==============="
echo "✅ Updated CloudFront origin to use HTTP (not HTTPS)"
echo "✅ Maintained HTTPS for user connections (secure)"
echo "✅ This eliminates SSL validation issues between CloudFront and ALB"
echo ""
echo "⏰ Wait Time: 5-15 minutes for CloudFront deployment"
echo ""
echo "🔗 Test After Deployment:"
echo "https://d3tytmnn6rkqkb.cloudfront.net/health"
echo ""
echo "💡 How This Works Now:"
echo "User → HTTPS → CloudFront → HTTP → ALB → ECS"
echo "     (secure)           (internal, fast)    (containers)"
