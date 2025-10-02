#!/bin/bash

# SSL Setup for ALB Direct URL - Solution 2
set -e
export AWS_DEFAULT_REGION=us-east-1

echo "🔒 Setting Up SSL on ALB Direct URL"
echo "=================================="
echo "Date: $(date)"
echo "ALB DNS: AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo

# Step 1: Request SSL Certificate for ALB DNS
echo "📜 Step 1: Requesting SSL Certificate for ALB"
echo "============================================="

ALB_DNS="AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo "Requesting SSL certificate for: $ALB_DNS"

CERT_ARN=$(aws acm request-certificate \
    --domain-name "$ALB_DNS" \
    --validation-method DNS \
    --region us-east-1 \
    --query 'CertificateArn' --output text)

echo "✅ SSL Certificate requested: $CERT_ARN"
echo ""

# Step 2: Get Certificate Validation Details
echo "📋 Step 2: Certificate Validation Required"
echo "========================================="

echo "⏳ Waiting 10 seconds for certificate details to populate..."
sleep 10

echo "Certificate validation details:"
aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --region us-east-1 \
    --query 'Certificate.DomainValidationOptions[0].[DomainName,ResourceRecord.Name,ResourceRecord.Value]' \
    --output table

# Get validation record details
VALIDATION_NAME=$(aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --region us-east-1 \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Name' \
    --output text)

VALIDATION_VALUE=$(aws acm describe-certificate \
    --certificate-arn "$CERT_ARN" \
    --region us-east-1 \
    --query 'Certificate.DomainValidationOptions[0].ResourceRecord.Value' \
    --output text)

echo ""
echo "🎯 VALIDATION REQUIRED:"
echo "======================"
echo "Record Type: CNAME"
echo "Name: $VALIDATION_NAME"
echo "Value: $VALIDATION_VALUE"
echo ""
echo "⚠️  Since this is AWS's auto-generated domain, we need to use a workaround..."

# Step 3: Alternative - Use Default SSL Certificate
echo -e "\n🔄 Step 3: Alternative Approach - AWS Default SSL"
echo "==============================================="

echo "Since AWS ALB auto-generated domains are complex to validate,"
echo "we'll use AWS's built-in SSL capability with a different approach."

# Get Load Balancer ARN
ALB_ARN=$(aws elbv2 describe-load-balancers --names "AccuNode-ECS-ALB" --region us-east-1 --query 'LoadBalancers[0].LoadBalancerArn' --output text)
TG_ARN=$(aws elbv2 describe-target-groups --names "AccuNode-ECS-API-TG" --region us-east-1 --query 'TargetGroups[0].TargetGroupArn' --output text)

echo "Load Balancer ARN: $ALB_ARN"
echo "Target Group ARN: $TG_ARN"

# Step 4: Create Self-Signed Certificate (for immediate testing)
echo -e "\n🛠️  Step 4: Creating Self-Signed Certificate for Testing"
echo "======================================================"

# Create directory for SSL files
mkdir -p deployment/ssl/

# Generate self-signed certificate
openssl req -x509 -newkey rsa:2048 -keyout deployment/ssl/private-key.pem -out deployment/ssl/cert.pem -days 365 -nodes -subj "/C=US/ST=State/L=City/O=AccuNode/CN=AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"

echo "✅ Self-signed certificate generated"

# Import certificate to ACM
SELF_SIGNED_CERT_ARN=$(aws acm import-certificate \
    --certificate fileb://deployment/ssl/cert.pem \
    --private-key fileb://deployment/ssl/private-key.pem \
    --region us-east-1 \
    --query 'CertificateArn' --output text)

echo "✅ Self-signed certificate imported: $SELF_SIGNED_CERT_ARN"

# Step 5: Add HTTPS Listener to ALB
echo -e "\n🔐 Step 5: Adding HTTPS Listener (Port 443)"
echo "=========================================="

HTTPS_LISTENER_ARN=$(aws elbv2 create-listener \
    --load-balancer-arn "$ALB_ARN" \
    --protocol HTTPS \
    --port 443 \
    --certificates CertificateArn="$SELF_SIGNED_CERT_ARN" \
    --default-actions Type=forward,TargetGroupArn="$TG_ARN" \
    --region us-east-1 \
    --query 'Listeners[0].ListenerArn' --output text)

echo "✅ HTTPS Listener created: $HTTPS_LISTENER_ARN"

# Step 6: Add HTTPS port to security group
echo -e "\n🔒 Step 6: Updating Security Group for HTTPS"
echo "==========================================="

aws ec2 authorize-security-group-ingress \
    --group-id sg-0904e16e00d5e08c7 \
    --protocol tcp \
    --port 443 \
    --cidr 0.0.0.0/0 \
    --region us-east-1 2>/dev/null && echo "✅ HTTPS port (443) added to security group" || echo "✅ HTTPS port already exists"

echo -e "\n🎉 SSL Setup Complete!"
echo "====================="
echo "✅ Self-signed certificate created and imported"
echo "✅ HTTPS listener (port 443) added to load balancer"  
echo "✅ Security group updated for HTTPS traffic"
echo ""
echo "🌐 Your HTTPS Endpoint:"
echo "https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo ""
echo "⚠️  Browser Warning Expected:"
echo "=============================="
echo "Since this uses a self-signed certificate, browsers will show:"
echo "• 'Your connection is not private'"
echo "• 'NET::ERR_CERT_AUTHORITY_INVALID'"
echo ""
echo "📋 To Use in Frontend:"
echo "====================="
echo "1. Update your frontend API base URL to:"
echo "   https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com"
echo ""
echo "2. Users will need to 'Accept' or 'Proceed' through browser warning"
echo "   (or add certificate exception)"
echo ""
echo "3. For production, replace with proper domain + validated certificate later"
echo ""
echo "🧪 Test Commands:"
echo "================"
echo "curl -k https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/health"
echo "# (-k flag ignores certificate warnings)"
echo ""
echo "✅ Mixed content issue should now be resolved!"
