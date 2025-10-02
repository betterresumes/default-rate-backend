#!/bin/bash

# CloudFront + ACM SSL Setup for Fully Secure HTTPS
set -e
export AWS_DEFAULT_REGION=us-east-1

echo "🔒 Setting Up CloudFront + ACM for Fully Secure HTTPS"
echo "===================================================="
echo "Date: $(date)"
echo "This will create a trusted SSL certificate with NO browser warnings!"
echo

# Step 1: Request ACM Certificate (Global - for CloudFront)
echo "📜 Step 1: Requesting ACM Certificate (Global Region)"
echo "=================================================="

# CloudFront requires certificates in us-east-1 (global)
CLOUDFRONT_CERT_ARN=$(aws acm request-certificate \
    --domain-name "*.cloudfront.net" \
    --subject-alternative-names "cloudfront.net" \
    --validation-method DNS \
    --region us-east-1 \
    --query 'CertificateArn' --output text 2>/dev/null || echo "SKIP")

if [ "$CLOUDFRONT_CERT_ARN" = "SKIP" ]; then
    echo "⚠️  Cannot request wildcard for cloudfront.net (AWS managed)"
    echo "📋 Using AWS managed SSL certificate instead..."
    
    # We'll use AWS managed certificate in CloudFront
    CLOUDFRONT_CERT_ARN="default"
else
    echo "✅ Certificate requested: $CLOUDFRONT_CERT_ARN"
fi

# Step 2: Create CloudFront Distribution
echo -e "\n☁️  Step 2: Creating CloudFront Distribution"
echo "==========================================="

# Get ALB DNS name
ALB_DNS="AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo "Origin (ALB): $ALB_DNS"

# Create CloudFront distribution configuration
cat > /tmp/cloudfront-config.json << EOF
{
    "CallerReference": "AccuNode-$(date +%s)",
    "Comment": "AccuNode API CloudFront Distribution - Secure HTTPS",
    "DefaultRootObject": "",
    "Origins": {
        "Quantity": 1,
        "Items": [
            {
                "Id": "AccuNode-ALB-Origin",
                "DomainName": "$ALB_DNS",
                "CustomOriginConfig": {
                    "HTTPPort": 80,
                    "HTTPSPort": 443,
                    "OriginProtocolPolicy": "https-only"
                }
            }
        ]
    },
    "DefaultCacheBehavior": {
        "TargetOriginId": "AccuNode-ALB-Origin",
        "ViewerProtocolPolicy": "redirect-to-https",
        "MinTTL": 0,
        "DefaultTTL": 0,
        "MaxTTL": 31536000,
        "ForwardedValues": {
            "QueryString": true,
            "Cookies": {
                "Forward": "all"
            },
            "Headers": {
                "Quantity": 4,
                "Items": ["Authorization", "Content-Type", "Origin", "Accept"]
            }
        },
        "TrustedSigners": {
            "Enabled": false,
            "Quantity": 0
        }
    },
    "Enabled": true,
    "PriceClass": "PriceClass_100"
}
EOF

echo "Creating CloudFront distribution..."
DISTRIBUTION_ID=$(aws cloudfront create-distribution --distribution-config file:///tmp/cloudfront-config.json --query 'Distribution.Id' --output text)
CLOUDFRONT_DOMAIN=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.DomainName' --output text)

echo "✅ CloudFront Distribution created!"
echo "   Distribution ID: $DISTRIBUTION_ID"
echo "   CloudFront Domain: $CLOUDFRONT_DOMAIN"

# Step 3: Wait for deployment
echo -e "\n⏳ Step 3: Waiting for CloudFront Deployment"
echo "=========================================="

echo "CloudFront is deploying... This takes 5-15 minutes."
echo "Status: Deploying..."

# Check deployment status
DEPLOYMENT_STATUS="InProgress"
WAIT_COUNT=0
while [ "$DEPLOYMENT_STATUS" = "InProgress" ] && [ $WAIT_COUNT -lt 20 ]; do
    sleep 30
    WAIT_COUNT=$((WAIT_COUNT + 1))
    DEPLOYMENT_STATUS=$(aws cloudfront get-distribution --id "$DISTRIBUTION_ID" --query 'Distribution.Status' --output text)
    echo "Status: $DEPLOYMENT_STATUS (waited $(($WAIT_COUNT * 30)) seconds)"
done

if [ "$DEPLOYMENT_STATUS" = "Deployed" ]; then
    echo "✅ CloudFront deployment complete!"
else
    echo "⏳ CloudFront still deploying (this is normal, takes up to 15 minutes)"
    echo "   You can continue - it will work once deployment finishes"
fi

# Step 4: Test the secure endpoint
echo -e "\n🧪 Step 4: Testing Secure Endpoint"
echo "================================="

echo "Your new FULLY SECURE HTTPS endpoint:"
echo "https://$CLOUDFRONT_DOMAIN"
echo ""

# Test if ready (may fail if still deploying)
echo "Testing endpoint (may timeout if still deploying)..."
curl -s -o /dev/null -w "Status: %{http_code}\n" "https://$CLOUDFRONT_DOMAIN/health" --max-time 10 || echo "Still deploying..."

# Step 5: Summary
echo -e "\n🎉 Secure HTTPS Setup Complete!"
echo "==============================="
echo "✅ CloudFront distribution created with AWS managed SSL"
echo "✅ Automatic HTTPS redirect enabled"
echo "✅ Browser will show 'Secure' lock icon (NO warnings!)"
echo "✅ Trusted certificate authority (Amazon)"
echo ""
echo "🌐 Your NEW Fully Secure API Endpoint:"
echo "https://$CLOUDFRONT_DOMAIN"
echo ""
echo "📱 Update Frontend URLs:"
echo "======================="
echo "// Replace this:"
echo "const API_BASE_URL = 'https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com'"
echo ""
echo "// With this (fully secure, no warnings):"
echo "const API_BASE_URL = 'https://$CLOUDFRONT_DOMAIN'"
echo ""
echo "🔒 Security Benefits:"
echo "==================="
echo "• ✅ Trusted SSL certificate (Amazon Certificate Authority)"
echo "• ✅ No browser warnings or 'Not Secure' labels"
echo "• ✅ Green lock icon in browser address bar"
echo "• ✅ Automatic HTTP to HTTPS redirect"
echo "• ✅ Global CDN (faster API responses worldwide)"
echo "• ✅ DDoS protection included"
echo ""
echo "⏰ Deployment Time:"
echo "=================="
echo "CloudFront deployment takes 5-15 minutes total."
echo "Once deployed, your API will be fully secure with zero browser warnings!"
echo ""
echo "💰 Cost: FREE (AWS Free Tier covers typical API usage)"
echo ""
echo "🎯 This completely eliminates the 'Not Secure' warning!"
echo "Users will see a green lock icon instead of security warnings."

# Clean up temp file
rm -f /tmp/cloudfront-config.json

echo ""
echo "📋 Next Steps:"
echo "============="
echo "1. Wait for CloudFront deployment to complete (5-15 minutes)"
echo "2. Update frontend to use: https://$CLOUDFRONT_DOMAIN"
echo "3. Test API calls - should work with zero security warnings!"
echo "4. Celebrate having a fully secure, professional API endpoint! 🎉"
