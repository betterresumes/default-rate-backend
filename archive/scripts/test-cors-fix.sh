#!/bin/bash

echo "🔧 CORS Fix - Testing and Verification"
echo "====================================="
echo "Date: $(date)"
echo

# Test 1: Check CloudFront distribution status
echo "1️⃣ CloudFront Distribution Status:"
echo "=================================="
DISTRIBUTION_STATUS=$(aws cloudfront get-distribution --id E22V6U663GQWNO --region us-east-1 --query 'Distribution.Status' --output text)
echo "Status: $DISTRIBUTION_STATUS"

if [ "$DISTRIBUTION_STATUS" = "InProgress" ]; then
    echo "⏳ CloudFront is still deploying. CORS changes may not be active yet."
elif [ "$DISTRIBUTION_STATUS" = "Deployed" ]; then
    echo "✅ CloudFront is fully deployed and ready for testing."
fi

echo

# Test 2: Check ECS deployment status
echo "2️⃣ ECS Service Deployment Status:"
echo "================================="
ECS_STATUS=$(aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service --region us-east-1 --query 'services[0].deployments[0].rolloutState' --output text)
echo "ECS Deployment: $ECS_STATUS"

if [ "$ECS_STATUS" = "IN_PROGRESS" ]; then
    echo "⏳ ECS is deploying new task definition with updated CORS origins."
elif [ "$ECS_STATUS" = "COMPLETED" ]; then
    echo "✅ ECS deployment completed. New CORS configuration is active."
fi

echo

# Test 3: Test CORS Preflight (OPTIONS)
echo "3️⃣ Testing CORS Preflight Request:"
echo "=================================="
echo "Testing OPTIONS request to CloudFront..."

# Test OPTIONS request
CORS_TEST=$(curl -X OPTIONS \
  https://d3tytmnn6rkqkb.cloudfront.net/api/v1/auth/register \
  -H 'Origin: https://client-eta-sepia.vercel.app' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: Content-Type,Authorization' \
  -s -o /dev/null -w "%{http_code}" \
  --max-time 10 || echo "TIMEOUT")

echo "OPTIONS Response Code: $CORS_TEST"

if [ "$CORS_TEST" = "200" ]; then
    echo "✅ CORS Preflight: SUCCESS! OPTIONS requests are now allowed."
elif [ "$CORS_TEST" = "403" ]; then
    echo "❌ CORS Preflight: Still getting 403. CloudFront may still be deploying."
elif [ "$CORS_TEST" = "TIMEOUT" ]; then
    echo "⏳ CORS Preflight: Timeout. CloudFront may still be updating."
else
    echo "⚠️  CORS Preflight: Got $CORS_TEST (unusual response)"
fi

echo

# Test 4: Test actual API endpoint
echo "4️⃣ Testing API Health Endpoint:"
echo "==============================="
HEALTH_TEST=$(curl -s https://d3tytmnn6rkqkb.cloudfront.net/health | jq -r '.status' 2>/dev/null || echo "ERROR")
echo "Health Status: $HEALTH_TEST"

if [ "$HEALTH_TEST" = "healthy" ]; then
    echo "✅ API Health: SUCCESS! Backend is responding correctly."
else
    echo "❌ API Health: Backend may still be starting up."
fi

echo

# Test 5: Show current CORS configuration
echo "5️⃣ Current CORS Configuration:"
echo "=============================="
echo "Allowed Origins in ECS Task Definition:"
echo "• https://accunode.ai"
echo "• https://client-eta-sepia.vercel.app" 
echo "• http://localhost:3000"
echo "• https://d3tytmnn6rkqkb.cloudfront.net"
echo ""
echo "CloudFront Allowed Methods:"
echo "• DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT"
echo ""
echo "CloudFront Forwarded Headers:"
echo "• Authorization, Origin, Accept, Content-Type"
echo "• Access-Control-Request-Method, Access-Control-Request-Headers"
echo "• Host, User-Agent"

echo

# Summary
echo "🎯 SUMMARY:"
echo "==========="
if [ "$DISTRIBUTION_STATUS" = "Deployed" ] && [ "$ECS_STATUS" = "COMPLETED" ] && [ "$CORS_TEST" = "200" ]; then
    echo "🎉 CORS FIX COMPLETE!"
    echo "✅ CloudFront: Deployed with all HTTP methods"
    echo "✅ ECS: New task definition with CloudFront domain in CORS origins"  
    echo "✅ CORS: OPTIONS requests working"
    echo ""
    echo "🚀 Your frontend should now work with:"
    echo "   Backend URL: https://d3tytmnn6rkqkb.cloudfront.net"
else
    echo "⏳ CORS FIX IN PROGRESS..."
    echo "Please wait 5-10 minutes and run this script again."
    echo ""
    echo "🔄 What's happening:"
    echo "• CloudFront: Deploying global edge cache updates"
    echo "• ECS: Rolling deployment with new CORS configuration"
    echo "• Total time: 5-15 minutes for full deployment"
fi

echo ""
echo "📞 Test Commands for Your Frontend:"
echo "==================================="
echo "# Test CORS manually:"
echo "curl -X OPTIONS 'https://d3tytmnn6rkqkb.cloudfront.net/api/v1/auth/register' \\"
echo "  -H 'Origin: https://your-frontend-domain.com' \\"
echo "  -H 'Access-Control-Request-Method: POST' \\"
echo "  -H 'Access-Control-Request-Headers: Content-Type,Authorization'"
echo ""
echo "# Test actual POST request:"
echo "curl -X POST 'https://d3tytmnn6rkqkb.cloudfront.net/api/v1/auth/register' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -H 'Origin: https://your-frontend-domain.com' \\"
echo "  -d '{\"email\":\"test@example.com\",\"password\":\"test123\"}'"
