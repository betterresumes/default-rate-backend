#!/bin/bash

# AccuNode AWS Infrastructure Setup Script
# Phase 1: VPC and Networking Infrastructure

set -e

echo "🚀 AccuNode AWS Deployment - Phase 1: Infrastructure Setup"
echo "========================================================"

# Configuration
PROJECT_NAME="accunode"
ENVIRONMENT="production"
AWS_REGION="${AWS_REGION:-us-east-1}"

echo "📋 Configuration:"
echo "   Project: $PROJECT_NAME"
echo "   Environment: $ENVIRONMENT"
echo "   Region: $AWS_REGION"
echo ""

# Step 1: Create VPC
echo "🏗️ Step 1: Creating VPC..."
VPC_ID=$(aws ec2 create-vpc \
    --cidr-block 10.0.0.0/16 \
    --query 'Vpc.VpcId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $VPC_ID \
    --tags Key=Name,Value="$PROJECT_NAME-vpc" \
           Key=Environment,Value="$ENVIRONMENT" \
    --region $AWS_REGION

echo "✅ VPC created: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute \
    --vpc-id $VPC_ID \
    --enable-dns-hostnames \
    --region $AWS_REGION

# Step 2: Create Internet Gateway
echo "🌐 Step 2: Creating Internet Gateway..."
IGW_ID=$(aws ec2 create-internet-gateway \
    --query 'InternetGateway.InternetGatewayId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $IGW_ID \
    --tags Key=Name,Value="$PROJECT_NAME-igw" \
           Key=Environment,Value="$ENVIRONMENT" \
    --region $AWS_REGION

aws ec2 attach-internet-gateway \
    --internet-gateway-id $IGW_ID \
    --vpc-id $VPC_ID \
    --region $AWS_REGION

echo "✅ Internet Gateway created and attached: $IGW_ID"

# Step 3: Create Public Subnets
echo "🏘️ Step 3: Creating Public Subnets..."

# Public Subnet 1 (for ALB and NAT)
PUBLIC_SUBNET_1=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.1.0/24 \
    --availability-zone "${AWS_REGION}a" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $PUBLIC_SUBNET_1 \
    --tags Key=Name,Value="$PROJECT_NAME-public-1a" \
           Key=Environment,Value="$ENVIRONMENT" \
           Key=Type,Value="public" \
    --region $AWS_REGION

# Public Subnet 2 (for ALB high availability)
PUBLIC_SUBNET_2=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.2.0/24 \
    --availability-zone "${AWS_REGION}b" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $PUBLIC_SUBNET_2 \
    --tags Key=Name,Value="$PROJECT_NAME-public-1b" \
           Key=Environment,Value="$ENVIRONMENT" \
           Key=Type,Value="public" \
    --region $AWS_REGION

echo "✅ Public subnets created:"
echo "   Subnet 1: $PUBLIC_SUBNET_1 (${AWS_REGION}a)"
echo "   Subnet 2: $PUBLIC_SUBNET_2 (${AWS_REGION}b)"

# Step 4: Create Private Subnets
echo "🔒 Step 4: Creating Private Subnets..."

# Private Subnet 1 (for EC2 instances)
PRIVATE_SUBNET_1=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.3.0/24 \
    --availability-zone "${AWS_REGION}a" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $PRIVATE_SUBNET_1 \
    --tags Key=Name,Value="$PROJECT_NAME-private-1a" \
           Key=Environment,Value="$ENVIRONMENT" \
           Key=Type,Value="private" \
    --region $AWS_REGION

# Private Subnet 2 (for RDS and Redis)
PRIVATE_SUBNET_2=$(aws ec2 create-subnet \
    --vpc-id $VPC_ID \
    --cidr-block 10.0.4.0/24 \
    --availability-zone "${AWS_REGION}b" \
    --query 'Subnet.SubnetId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $PRIVATE_SUBNET_2 \
    --tags Key=Name,Value="$PROJECT_NAME-private-1b" \
           Key=Environment,Value="$ENVIRONMENT" \
           Key=Type,Value="private" \
    --region $AWS_REGION

echo "✅ Private subnets created:"
echo "   Subnet 1: $PRIVATE_SUBNET_1 (${AWS_REGION}a)"
echo "   Subnet 2: $PRIVATE_SUBNET_2 (${AWS_REGION}b)"

# Step 5: Create Route Tables
echo "🗺️ Step 5: Creating Route Tables..."

# Public Route Table
PUBLIC_RT=$(aws ec2 create-route-table \
    --vpc-id $VPC_ID \
    --query 'RouteTable.RouteTableId' \
    --output text \
    --region $AWS_REGION)

aws ec2 create-tags \
    --resources $PUBLIC_RT \
    --tags Key=Name,Value="$PROJECT_NAME-public-rt" \
           Key=Environment,Value="$ENVIRONMENT" \
    --region $AWS_REGION

# Add route to Internet Gateway
aws ec2 create-route \
    --route-table-id $PUBLIC_RT \
    --destination-cidr-block 0.0.0.0/0 \
    --gateway-id $IGW_ID \
    --region $AWS_REGION

# Associate public subnets with public route table
aws ec2 associate-route-table \
    --subnet-id $PUBLIC_SUBNET_1 \
    --route-table-id $PUBLIC_RT \
    --region $AWS_REGION

aws ec2 associate-route-table \
    --subnet-id $PUBLIC_SUBNET_2 \
    --route-table-id $PUBLIC_RT \
    --region $AWS_REGION

echo "✅ Route tables configured"

# Step 6: Save configuration to file
echo "💾 Step 6: Saving infrastructure configuration..."
cat > infrastructure.json << EOF
{
  "project_name": "$PROJECT_NAME",
  "environment": "$ENVIRONMENT",
  "region": "$AWS_REGION",
  "vpc_id": "$VPC_ID",
  "internet_gateway_id": "$IGW_ID",
  "public_subnet_1": "$PUBLIC_SUBNET_1",
  "public_subnet_2": "$PUBLIC_SUBNET_2",
  "private_subnet_1": "$PRIVATE_SUBNET_1",
  "private_subnet_2": "$PRIVATE_SUBNET_2",
  "public_route_table": "$PUBLIC_RT"
}
EOF

echo "✅ Infrastructure configuration saved to infrastructure.json"
echo ""
echo "🎉 Phase 1 Complete! Infrastructure setup successful."
echo ""
echo "📋 Summary:"
echo "   VPC ID: $VPC_ID"
echo "   Internet Gateway: $IGW_ID"
echo "   Public Subnets: $PUBLIC_SUBNET_1, $PUBLIC_SUBNET_2"
echo "   Private Subnets: $PRIVATE_SUBNET_1, $PRIVATE_SUBNET_2"
echo ""
echo "⏭️ Next: Run 02-security-groups.sh to set up security groups"
