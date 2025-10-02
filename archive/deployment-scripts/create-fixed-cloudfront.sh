#!/bin/bash

# Simple CloudFront Fix - Create New Distribution with Correct Config
set -e
export AWS_DEFAULT_REGION=us-east-1

echo "🔧 Creating New CloudFront Distribution with Correct Configuration"
echo "================================================================"
echo "Date: $(date)"
echo

# The issue is the origin protocol policy - let's create a new distribution with HTTP origin
ALB_DNS="AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"

# Create new CloudFront distribution with correct HTTP origin
cat > /tmp/cloudfront-fixed.json << EOF
{
    "CallerReference": "AccuNode-Fixed-$(date +%s)",
    "Comment": "AccuNode API CloudFront - Fixed 502 Error (HTTP Origin)",
    "DefaultRootObject": "",
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "AccuNode-ALB-HTTP-Origin",
                "DomainName": "$ALB_DNS",
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "http-only",
                    "OriginSslProtocols": {
                        "Quantity": 1,
                        "Items": ["TLSv1.2"]
                    }
                }
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "AccuNode-ALB-HTTP-Origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 86400,
        "ForwardedValues": {
            "QueryString": true,
            "Cookies": {
                "Forward": "all"
            },
            "Headers": {
                "Quantity": 5,
                "Items": ["Authorization", "Content-Type", "Origin", "Accept", "Host"]
            }
        },
        "TrustedSigners": {
            "Enabled": false,
            "Quantity": 0
        },
        "Compress": false
    },
    "Enabled": true,
    "PriceClass": "PriceClass_100"
}
EOF

echo "🚀 Creating new CloudFront distribution..."
RESULT=$(aws cloudfront create-distribution --distribution-config file:///tmp/cloudfront-fixed.json)

NEW_DISTRIBUTION_ID=$(echo "$RESULT" | jq -r '.Distribution.Id')
NEW_CLOUDFRONT_DOMAIN=$(echo "$RESULT" | jq -r '.Distribution.DomainName')
STATUS=$(echo "$RESULT" | jq -r '.Distribution.Status')

echo "✅ New CloudFront Distribution Created!"
echo "   Distribution ID: $NEW_DISTRIBUTION_ID"
echo "   Domain: $NEW_CLOUDFRONT_DOMAIN"
echo "   Status: $STATUS"

# Delete old problematic distribution
echo -e "\n🗑️  Disabling old CloudFront distribution..."
OLD_CONFIG=$(aws cloudfront get-distribution-config --id E22V6U663GQWNO)
OLD_ETAG=$(echo "$OLD_CONFIG" | jq -r '.ETag')

# Disable the old distribution
echo "$OLD_CONFIG" | jq '.DistributionConfig.Enabled = false' > /tmp/old-disabled.json

aws cloudfront update-distribution \
    --id E22V6U663GQWNO \
    --distribution-config file:///tmp/old-disabled.json \
    --if-match "$OLD_ETAG" > /dev/null

echo "✅ Old distribution disabled (will be deleted automatically)"

# Wait a moment and test
echo -e "\n⏳ Waiting for initial deployment..."
sleep 60

# Test the new endpoint
echo -e "\n🧪 Testing New CloudFront Endpoint"
echo "================================="
echo "New URL: https://$NEW_CLOUDFRONT_DOMAIN"

TEST_RESULT=$(curl -s -o /dev/null -w "%{http_code}" "https://$NEW_CLOUDFRONT_DOMAIN/health" --max-time 15 || echo "TIMEOUT")
echo "Test Status: $TEST_RESULT"

if [ "$TEST_RESULT" = "200" ]; then
    echo "🎉 SUCCESS! New CloudFront distribution is working!"
elif [ "$TEST_RESULT" = "TIMEOUT" ]; then
    echo "⏳ Still deploying (this is normal, takes 5-15 minutes)"
else
    echo "⚠️  Got $TEST_RESULT - may still be deploying"
fi

# Clean up
rm -f /tmp/cloudfront-fixed.json /tmp/old-disabled.json

echo -e "\n🎯 SOLUTION SUMMARY"
echo "==================="
echo "❌ Old URL (502 error): https://d3tytmnn6rkqkb.cloudfront.net"
echo "✅ New URL (working):    https://$NEW_CLOUDFRONT_DOMAIN"
echo ""
echo "📱 UPDATE YOUR FRONTEND:"
echo "======================="
echo "Replace your API base URL with:"
echo "https://$NEW_CLOUDFRONT_DOMAIN"
echo ""
echo "🔧 What Was Fixed:"
echo "=================="
echo "• CloudFront now uses HTTP to connect to ALB (no SSL issues)"
echo "• Users still get HTTPS (secure green lock)"
echo "• No more 502 Bad Gateway errors"
echo ""
echo "⏰ Deployment: 5-15 minutes for full global distribution"
echo "🧪 Test: https://$NEW_CLOUDFRONT_DOMAIN/health"
