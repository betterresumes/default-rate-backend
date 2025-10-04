#!/bin/bash
# 🚀 AccuNode Complete AWS Deployment Script
# CLI-Only Automated Deployment

set -e  # Exit on any error

echo "=========================================="
echo "🚀 AccuNode AWS Deployment Starting..."
echo "=========================================="

# Check if required tools are installed
command -v aws >/dev/null 2>&1 || { echo "❌ AWS CLI is required but not installed. Install: brew install awscli"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed. Install Docker Desktop"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo "❌ jq is required but not installed. Install: brew install jq"; exit 1; }

# Configuration (UPDATE THESE VALUES)
export DOMAIN_NAME="skip-ssl"  # Using AWS Load Balancer DNS (no custom domain)
export YOUR_EMAIL="accunodeai@gmail.com"  # Email for AWS notifications and alerts
export AWS_REGION="us-east-1"

# CONFIGURATION CHOICE: No Custom Domain (HTTP only via AWS ALB DNS)
# Your AccuNode app will be accessible at: http://accunode-alb-xxxxx.us-east-1.elb.amazonaws.com
# Benefits: No domain costs, faster setup, can add domain later
# Note: HTTP only (no HTTPS) - fine for development/testing

echo "📋 Configuration Check:"
echo "Domain: $DOMAIN_NAME"
echo "Email: $YOUR_EMAIL"
echo "Region: $AWS_REGION"
echo ""

if [ "$YOUR_EMAIL" = "your-email@example.com" ]; then
    echo "❌ Please update YOUR_EMAIL in this script first!"
    exit 1
fi

if [ "$DOMAIN_NAME" = "skip-ssl" ]; then
    echo "🌐 Configuration: Using AWS Load Balancer DNS (no custom domain)"
    echo "📝 SSL setup will be skipped - app will use HTTP only"
    echo "💰 Cost savings: No domain registration fees (~$12/year saved)"
elif [ -z "$DOMAIN_NAME" ] || [ "$DOMAIN_NAME" = "your-domain.com" ]; then
    echo "❌ Please set DOMAIN_NAME to either:"
    echo "   - Your domain: 'mydomain.com'"  
    echo "   - Skip SSL: 'skip-ssl'"
    exit 1
fi

# Generate unique identifiers
export TIMESTAMP=$(date +%s)
export BUCKET_NAME="accunode-ml-models-prod-$TIMESTAMP"

# Generate secure credentials
echo "🔐 Generating secure credentials..."
export DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)
export SECRET_KEY=$(openssl rand -base64 32)
export JWT_SECRET=$(openssl rand -base64 32)

# Save all configuration
cat > accunode-deployment-config.env << EOF
# AccuNode Deployment Configuration
DOMAIN_NAME=$DOMAIN_NAME
YOUR_EMAIL=$YOUR_EMAIL
BUCKET_NAME=$BUCKET_NAME
DB_PASSWORD=$DB_PASSWORD
SECRET_KEY=$SECRET_KEY
JWT_SECRET=$JWT_SECRET
AWS_REGION=$AWS_REGION
TIMESTAMP=$TIMESTAMP
EOF

echo "✅ Configuration saved to: accunode-deployment-config.env"
echo ""
echo "📋 Generated Values:"
echo "S3 Bucket: $BUCKET_NAME"
echo "Database Password: $DB_PASSWORD"
echo "Timestamp: $TIMESTAMP"
echo ""

# Create deployment status tracker
cat > deployment-status.log << EOF
AccuNode Deployment Status - $(date)
====================================
PHASE 1: Infrastructure - PENDING
PHASE 2: Databases - PENDING  
PHASE 3: Storage - PENDING
PHASE 4: Container - PENDING
PHASE 5: Load Balancer - PENDING
PHASE 6: SSL - PENDING
PHASE 7: Monitoring - PENDING
PHASE 8: CI/CD - PENDING
EOF

echo "📊 Deployment status tracker created: deployment-status.log"
echo ""
echo "🎯 NEXT STEPS:"
echo "1. Verify AWS CLI is configured: aws sts get-caller-identity"
echo "2. Run the deployment phases from DEPLOYMENT_GUIDE.md"
echo "3. Each phase will update deployment-status.log automatically"
echo ""
echo "🚀 Ready to deploy AccuNode!"
echo ""
echo "=== QUICK START COMMAND ==="
echo "Source the config and start Phase 1:"
echo "source accunode-deployment-config.env"
echo "aws sts get-caller-identity  # Verify AWS access"
echo ""
echo "Then follow DEPLOYMENT_GUIDE.md starting from Phase 1..."
