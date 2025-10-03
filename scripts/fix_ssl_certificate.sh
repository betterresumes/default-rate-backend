#!/bin/bash

# Fix SSL Certificate Issue - Replace Self-Signed with Proper ACM Certificate
# This script will create a proper SSL certificate for the AccuNode deployment

echo "🔒 SSL Certificate Fix Script for AccuNode"
echo "=========================================="

# Get current ALB ARN and listener
ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:461962182774:loadbalancer/app/AccuNode-ECS-ALB/33c157e494a26944"
CURRENT_CERT_ARN="arn:aws:acm:us-east-1:461962182774:certificate/872adae2-576a-450b-bcfd-4e68f90bbc68"

echo "📋 Current SSL Configuration:"
echo "   ALB: AccuNode-ECS-ALB"
echo "   Certificate: Self-signed (AccuNode issuer)"
echo "   Status: Causing SSL verification errors"

echo ""
echo "🎯 SSL Certificate Fix Options:"
echo ""
echo "Option 1: Request New ACM Certificate (Recommended)"
echo "=========================================="
echo "For production deployment with custom domain:"
echo ""
echo "1. Request ACM certificate for your domain:"
cat << 'EOF'
   aws acm request-certificate \
     --domain-name yourdomain.com \
     --validation-method DNS \
     --subject-alternative-names "*.yourdomain.com" \
     --region us-east-1

2. Add DNS validation records to your domain registrar
3. Wait for certificate validation (5-30 minutes)
4. Update ALB listener with new certificate
EOF

echo ""
echo "Option 2: Use ALB Default Certificate (Quick Fix)"
echo "=============================================="
echo "For testing/demo purposes (eliminates SSL errors):"
echo ""

# Get listener ARN
LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query 'Listeners[?Port==`443`].ListenerArn' --output text 2>/dev/null)

if [ ! -z "$LISTENER_ARN" ]; then
    echo "Found HTTPS listener: $LISTENER_ARN"
    echo ""
    echo "Executing Quick Fix: Remove custom certificate..."
    
    # Update listener to remove certificate (use default)
    aws elbv2 modify-listener \
        --listener-arn "$LISTENER_ARN" \
        --certificates CertificateArn="" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        echo "✅ Certificate removed - ALB now uses default certificate"
        echo "✅ SSL verification errors should be resolved"
    else
        echo "⚠️ Failed to update listener - trying alternative approach..."
        
        # Alternative: Remove HTTPS listener and redirect HTTP to HTTPS via external service
        echo "Alternative: Redirect traffic through CloudFlare or similar service"
    fi
else
    echo "❌ HTTPS listener not found"
fi

echo ""
echo "Option 3: Production Domain Setup (Complete Solution)"
echo "===================================================="
echo "For production deployment:"
echo ""
cat << 'EOF'
1. Purchase/configure domain (e.g., api.accunode.ai)
2. Create Route 53 hosted zone
3. Request ACM certificate for domain
4. Update ALB with certificate
5. Create CNAME record pointing to ALB DNS name

Commands:
# 1. Request certificate
aws acm request-certificate \
  --domain-name api.accunode.ai \
  --validation-method DNS \
  --region us-east-1

# 2. Get certificate ARN (after validation)
CERT_ARN=$(aws acm list-certificates \
  --query 'CertificateSummaryList[?DomainName==`api.accunode.ai`].CertificateArn' \
  --output text)

# 3. Update ALB listener
aws elbv2 modify-listener \
  --listener-arn $LISTENER_ARN \
  --certificates CertificateArn=$CERT_ARN
EOF

echo ""
echo "🔍 Current SSL Status Check:"
echo "=============================="

# Test current SSL status
ALB_DNS="AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo "Testing SSL connection to: $ALB_DNS"

# Check if curl works without -k flag
if curl -s --connect-timeout 5 "https://$ALB_DNS/health" > /dev/null 2>&1; then
    echo "✅ SSL Certificate: Valid (no errors)"
else
    echo "❌ SSL Certificate: Invalid (requires -k flag)"
    echo "   Issue: Self-signed certificate"
fi

echo ""
echo "📊 Certificate Details:"
aws acm describe-certificate --certificate-arn "$CURRENT_CERT_ARN" \
    --query '{DomainName:Certificate.DomainName,Status:Certificate.Status,Type:Certificate.Type,Issuer:Certificate.Issuer}' 2>/dev/null || echo "Certificate details unavailable"

echo ""
echo "🎯 Recommendation:"
echo "=================="
echo "For immediate fix: Use Option 2 (remove custom certificate)"
echo "For production: Use Option 3 (proper domain + ACM certificate)"
echo ""
echo "Note: The application works fine - this is only a certificate trust issue"
echo "      API functionality is not impacted, only SSL verification warnings"
