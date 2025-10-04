#!/bin/bash
# 🔍 Find Your VPC and Subnet Details for RDS Access

echo "🔍 FINDING YOUR VPC CONFIGURATION"
echo "=" * 40

# Find RDS instance details
echo "📋 Finding RDS instance details..."
RDS_INFO=$(aws rds describe-db-instances --db-instance-identifier accunode-postgres --output json 2>/dev/null)

if [[ $? -eq 0 ]]; then
    VPC_ID=$(echo "$RDS_INFO" | jq -r '.DBInstances[0].DBSubnetGroup.VpcId')
    RDS_SUBNETS=$(echo "$RDS_INFO" | jq -r '.DBInstances[0].DBSubnetGroup.Subnets[].SubnetId' | tr '\n' ' ')
    RDS_AZ=$(echo "$RDS_INFO" | jq -r '.DBInstances[0].AvailabilityZone')
    
    echo "✅ Found RDS in VPC: $VPC_ID"
    echo "📍 RDS Availability Zone: $RDS_AZ"
    echo "🔗 RDS Subnets: $RDS_SUBNETS"
else
    echo "❌ Could not find RDS instance 'accunode-postgres'"
    echo "   Please check the RDS instance name and your AWS credentials"
    exit 1
fi

# Find subnets in the same VPC
echo ""
echo "🔍 Finding subnets in VPC $VPC_ID..."
SUBNETS=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --output json)

# Find private subnets (usually where RDS is)
echo ""
echo "📋 PRIVATE SUBNETS (for bastion host):"
PRIVATE_SUBNETS=$(echo "$SUBNETS" | jq -r '.Subnets[] | select(.MapPublicIpOnLaunch == false) | "\(.SubnetId) - \(.AvailabilityZone) - \(.CidrBlock)"')
echo "$PRIVATE_SUBNETS"

# Find public subnets (for internet access)
echo ""
echo "📋 PUBLIC SUBNETS (if needed):"
PUBLIC_SUBNETS=$(echo "$SUBNETS" | jq -r '.Subnets[] | select(.MapPublicIpOnLaunch == true) | "\(.SubnetId) - \(.AvailabilityZone) - \(.CidrBlock)"')
if [[ -n "$PUBLIC_SUBNETS" ]]; then
    echo "$PUBLIC_SUBNETS"
else
    echo "   No public subnets found in this VPC"
fi

# Get first private subnet for RDS access
FIRST_PRIVATE_SUBNET=$(echo "$SUBNETS" | jq -r '.Subnets[] | select(.MapPublicIpOnLaunch == false) | .SubnetId' | head -1)
FIRST_PUBLIC_SUBNET=$(echo "$SUBNETS" | jq -r '.Subnets[] | select(.MapPublicIpOnLaunch == true) | .SubnetId' | head -1)

echo ""
echo "🎯 RECOMMENDED CONFIGURATION:"
echo "=" * 40
echo "VPC_ID=\"$VPC_ID\""
echo "PRIVATE_SUBNET_ID=\"$FIRST_PRIVATE_SUBNET\"  # Use this for bastion host"
if [[ -n "$FIRST_PUBLIC_SUBNET" ]]; then
    echo "PUBLIC_SUBNET_ID=\"$FIRST_PUBLIC_SUBNET\"   # For internet access (optional)"
else
    echo "# No public subnet available - bastion will be private only"
fi
echo ""

# Create updated setup script
echo "📝 Creating updated bastion setup script..."
sed "s/VPC_ID=\"vpc-xxxxxxxxx\"/VPC_ID=\"$VPC_ID\"/" scripts/setup-vpc-bastion.sh > scripts/setup-vpc-bastion-configured.sh
sed -i "s/PRIVATE_SUBNET_ID=\"subnet-xxxxxxx\"/PRIVATE_SUBNET_ID=\"$FIRST_PRIVATE_SUBNET\"/" scripts/setup-vpc-bastion-configured.sh

if [[ -n "$FIRST_PUBLIC_SUBNET" ]]; then
    sed -i "s/PUBLIC_SUBNET_ID=\"subnet-xxxxxxx\"/PUBLIC_SUBNET_ID=\"$FIRST_PUBLIC_SUBNET\"/" scripts/setup-vpc-bastion-configured.sh
else
    sed -i "s/PUBLIC_SUBNET_ID=\"subnet-xxxxxxx\"/PUBLIC_SUBNET_ID=\"$FIRST_PRIVATE_SUBNET\"/" scripts/setup-vpc-bastion-configured.sh
fi

chmod +x scripts/setup-vpc-bastion-configured.sh

echo "✅ Created configured setup script: scripts/setup-vpc-bastion-configured.sh"
echo ""
echo "🚀 NEXT STEPS:"
echo "1. Review the configuration above"
echo "2. Run: ./scripts/setup-vpc-bastion-configured.sh"
echo "3. Connect: aws ssm start-session --target <instance-id>"
echo "4. Create admin: python3 create_super_admin.py"
