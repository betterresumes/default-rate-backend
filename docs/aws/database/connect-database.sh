#!/bin/bash

# AccuNode Database Connection Helper
# This script helps team members quickly connect to the database via bastion

set -e

echo "🗄️ AccuNode Database Connection Helper"
echo "======================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi

# Check if user is authenticated
if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not configured. Run 'aws configure' first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ AWS CLI configured${NC}"

# Get bastion instance information
echo ""
echo "🔍 Finding bastion instance..."

BASTION_INFO=$(aws ec2 describe-instances \
    --filters "Name=tag:Name,Values=AccuNode-Bastion" "Name=instance-state-name,Values=running" \
    --query 'Reservations[0].Instances[0].[InstanceId,PublicIpAddress,State.Name]' \
    --output text 2>/dev/null)

if [ -z "$BASTION_INFO" ] || [ "$BASTION_INFO" = "None	None	None" ]; then
    echo -e "${RED}❌ Bastion instance not found or not running${NC}"
    echo "Please check if the bastion instance exists and is running."
    exit 1
fi

INSTANCE_ID=$(echo $BASTION_INFO | cut -f1)
PUBLIC_IP=$(echo $BASTION_INFO | cut -f2)
STATE=$(echo $BASTION_INFO | cut -f3)

echo -e "${GREEN}✅ Bastion found:${NC}"
echo "   Instance ID: $INSTANCE_ID"
echo "   Public IP: $PUBLIC_IP"
echo "   State: $STATE"

# Get RDS endpoint
echo ""
echo "🗄️ Finding database endpoint..."

DB_ENDPOINT=$(aws rds describe-db-instances \
    --db-instance-identifier accunode-postgres \
    --query 'DBInstances[0].Endpoint.Address' \
    --output text 2>/dev/null)

if [ -z "$DB_ENDPOINT" ] || [ "$DB_ENDPOINT" = "None" ]; then
    echo -e "${RED}❌ Database endpoint not found${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Database endpoint: $DB_ENDPOINT${NC}"

# Check if SSH key exists
SSH_KEY="bastion-access-key.pem"
if [ ! -f "$SSH_KEY" ]; then
    echo -e "${YELLOW}⚠️  SSH key file not found: $SSH_KEY${NC}"
    echo "Please ensure the SSH key file is in the current directory."
    echo ""
fi

# Display connection instructions
echo ""
echo "🚀 Connection Instructions:"
echo "=========================="

echo ""
echo -e "${YELLOW}Method 1: Direct SSH + Database Connection${NC}"
echo "1. SSH to bastion:"
echo "   ssh -i $SSH_KEY ec2-user@$PUBLIC_IP"
echo ""
echo "2. From bastion, connect to database:"
echo "   psql -h $DB_ENDPOINT -U admin -d accunode_production -p 5432"
echo ""

echo -e "${YELLOW}Method 2: SSH Tunnel (Recommended for local development)${NC}"
echo "1. Create SSH tunnel (keep this terminal open):"
echo "   ssh -i $SSH_KEY -L 5432:$DB_ENDPOINT:5432 ec2-user@$PUBLIC_IP"
echo ""
echo "2. From another terminal, connect locally:"
echo "   psql -h localhost -U admin -d accunode_production -p 5432"
echo ""

echo -e "${YELLOW}Method 3: Quick Connection Script${NC}"
echo "Run this command to connect directly:"
echo "   ssh -i $SSH_KEY -t ec2-user@$PUBLIC_IP \"psql -h $DB_ENDPOINT -U admin -d accunode_production -p 5432\""
echo ""

# Offer to create connection aliases
echo "💡 Tip: Add these to your ~/.bashrc or ~/.zshrc for quick access:"
echo ""
echo "alias accunode-bastion='ssh -i $SSH_KEY ec2-user@$PUBLIC_IP'"
echo "alias accunode-db-tunnel='ssh -i $SSH_KEY -L 5432:$DB_ENDPOINT:5432 ec2-user@$PUBLIC_IP'"
echo "alias accunode-db='psql -h localhost -U admin -d accunode_production -p 5432'"
echo ""

# Security reminders
echo -e "${RED}🔒 Security Reminders:${NC}"
echo "- Ensure SSH key file has correct permissions: chmod 400 $SSH_KEY"
echo "- Never share SSH keys or database credentials"
echo "- Close connections when done"
echo "- Only access database through bastion host"
echo ""

echo "📚 For detailed instructions, see: docs/aws/database/COMPLETE_DATABASE_ACCESS_GUIDE.md"
echo ""
echo -e "${GREEN}Happy querying! 🎉${NC}"
