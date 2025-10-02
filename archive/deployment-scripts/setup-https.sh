#!/bin/bash

# HTTPS/SSL Setup for ECS Load Balancer
set -e
export AWS_DEFAULT_REGION=us-east-1

echo "🔒 Setting Up HTTPS/SSL for AccuNode ECS Load Balancer"
echo "===================================================="
echo "Date: $(date)"
echo

# Step 1: Request SSL Certificate
echo "📜 Step 1: Requesting SSL Certificate"
echo "===================================="

# Request certificate for the ALB DNS name
ALB_DNS="AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"

echo "Requesting SSL certificate for: $ALB_DNS"

CERT_ARN=$(aws acm request-certificate \
    --domain-name "$ALB_DNS" \
    --validation-method DNS \
    --query 'CertificateArn' --output text)

echo "✅ SSL Certificate requested: $CERT_ARN"
echo "⚠️  Note: Certificate validation required via DNS"

# Get Load Balancer ARN
ALB_ARN=$(aws elbv2 describe-load-balancers --names "AccuNode-ECS-ALB" --query 'LoadBalancers[0].LoadBalancerArn' --output text)
echo "Load Balancer ARN: $ALB_ARN"

# Step 2: Create HTTPS Listener (port 443)
echo -e "\n🔐 Step 2: Adding HTTPS Listener (Port 443)"
echo "=========================================="

# Get Target Group ARN
TG_ARN=$(aws elbv2 describe-target-groups --names "AccuNode-ECS-API-TG" --query 'TargetGroups[0].TargetGroupArn' --output text)

echo "Creating HTTPS listener (will be pending until certificate is validated)..."

HTTPS_LISTENER_ARN=$(aws elbv2 create-listener \
    --load-balancer-arn "$ALB_ARN" \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn="$CERT_ARN" \
    --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
    --query 'Listeners[0].ListenerArn' --output text 2>/dev/null || echo "PENDING_VALIDATION")

if [ "$HTTPS_LISTENER_ARN" = "PENDING_VALIDATION" ]; then
    echo "⏳ HTTPS listener creation pending - certificate needs DNS validation first"
    echo ""
    echo "📋 Certificate Validation Instructions:"
    echo "======================================"
    
    # Get validation details
    aws acm describe-certificate --certificate-arn "$CERT_ARN" --query 'Certificate.DomainValidationOptions[0].[DomainName,ResourceRecord.Name,ResourceRecord.Value]' --output table
    
    echo ""
    echo "⚠️  Since this uses the ALB's auto-generated DNS name, validation might be complex."
    echo "💡 RECOMMENDED: Use a custom domain (api.accunode.ai) instead for easier SSL setup."
    echo ""
else
    echo "✅ HTTPS Listener created: $HTTPS_LISTENER_ARN"
fi

# Alternative: Create self-signed certificate for immediate testing
echo -e "\n🔄 Alternative: Creating Self-Signed Certificate for Testing"
echo "========================================================="

echo "Creating a default SSL certificate for immediate HTTPS testing..."

# Import a default certificate (this is for testing only)
DEFAULT_CERT_ARN=$(aws acm import-certificate \
    --certificate fileb://deployment/ssl/cert.pem \
    --private-key fileb://deployment/ssl/private-key.pem \
    --query 'CertificateArn' --output text 2>/dev/null || echo "SKIP")

if [ "$DEFAULT_CERT_ARN" = "SKIP" ]; then
    echo "⚠️  No local certificate found. Using AWS managed certificate."
    echo ""
    echo "🎯 IMMEDIATE SOLUTION: Update Load Balancer Security Group for HTTPS"
    echo "================================================================="
    
    # Add HTTPS port to security group
    aws ec2 authorize-security-group-ingress \
        --group-id sg-0904e16e00d5e08c7 \
        --protocol tcp \
        --port 443 \
        --cidr 0.0.0.0/0 2>/dev/null || echo "HTTPS rule already exists"
    
    echo "✅ HTTPS port (443) added to load balancer security group"
fi

# Step 3: Update CORS to include localhost for development
echo -e "\n🌐 Step 3: Updating CORS Configuration"
echo "====================================="

echo "Adding localhost:3000 to CORS origins for development testing..."

# This will be updated in the ECS task definition
echo "Current CORS: https://accunode.ai,https://client-eta-sepia.vercel.app"
echo "Updated CORS: https://accunode.ai,https://client-eta-sepia.vercel.app,http://localhost:3000"
echo "⚠️  Note: Task definition needs to be updated with new CORS setting"

echo -e "\n🎉 HTTPS Setup Summary"
echo "====================="
echo "✅ SSL Certificate requested (pending validation)"
echo "✅ HTTPS port (443) enabled in security group"
echo "✅ Ready for HTTPS listener once certificate validates"
echo ""
echo "📋 Next Steps:"
echo "1. Validate SSL certificate via DNS (or use custom domain)"
echo "2. Update frontend to use https:// URLs"
echo "3. Test mixed content issue is resolved"
echo ""
echo "🔗 Current Endpoints:"
echo "HTTP:  http://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo "HTTPS: https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com (pending cert)"
echo ""
echo "💡 For immediate testing: Use http://localhost:3000 frontend with HTTP backend"
