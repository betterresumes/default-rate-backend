# 🚀 **Complete CLI-Only AWS Deployment Guide - AccuNode**

## 📋 **Repository Information**
- **Project Name**: AccuNode
- **Main Repo**: https://github.com/accunodeai/server
- **Deployment Branch**: `prod`
- **Priority**: Critical components first, CLI-only deployment

---

# **🚀 OPTION 1: COMPLETE AUTOMATED CLI SCRIPT**

If you want to deploy everything in one go, use this complete automation script:

```bash
#!/bin/bash
# AccuNode Complete AWS Deployment Script
# Run this script for fully automated deployment

set -e  # Exit on any error

echo "🚀 Starting AccuNode AWS Deployment..."

# Configuration
export DOMAIN_NAME="your-domain.com"  # CHANGE THIS
export YOUR_EMAIL="your-email@example.com"  # CHANGE THIS
export AWS_REGION="us-east-1"

# Generate unique identifiers
export TIMESTAMP=$(date +%s)
export BUCKET_NAME="accunode-ml-models-prod-$TIMESTAMP"

# Database credentials
export DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)
export SECRET_KEY=$(openssl rand -base64 32)
export JWT_SECRET=$(openssl rand -base64 32)

echo "📋 Configuration:"
echo "Domain: $DOMAIN_NAME"
echo "Email: $YOUR_EMAIL"
echo "S3 Bucket: $BUCKET_NAME"
echo "Database Password: $DB_PASSWORD"

# Save credentials
cat > accunode-deployment-config.env << EOF
DOMAIN_NAME=$DOMAIN_NAME
YOUR_EMAIL=$YOUR_EMAIL
BUCKET_NAME=$BUCKET_NAME
DB_PASSWORD=$DB_PASSWORD
SECRET_KEY=$SECRET_KEY
JWT_SECRET=$JWT_SECRET
EOF

echo "✅ Configuration saved to accunode-deployment-config.env"

# Now run the step-by-step deployment below...
echo "🎯 Continue with the step-by-step deployment for detailed control"
echo "   Or copy each section below and run sequentially"
```

Save this as `deploy-accunode.sh` and run: `chmod +x deploy-accunode.sh && ./deploy-accunode.sh`

---

# **🔧 OPTION 2: STEP-BY-STEP CLI DEPLOYMENT**

# **PHASE 1: PREREQUISITES & SETUP (Day 1)**

## **Step 1: AWS Account Setup**

### **1.1 Create AWS Account**
```bash
# Visit: https://aws.amazon.com/
# Sign up for AWS account
# Enable billing alerts
# Set up MFA for root account
```

### **1.2 Install AWS CLI**
```bash
# macOS
brew install awscli

# Verify installation
aws --version
```

### **1.3 Create IAM User for Deployment (CLI-Only)**
```bash
# Create IAM user
aws iam create-user --user-name accunode-deployment

# Create and attach policies directly via CLI
cat > deployment-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ecs:*",
                "ec2:*",
                "rds:*",
                "elasticache:*",
                "s3:*",
                "ssm:*",
                "route53:*",
                "acm:*",
                "iam:*",
                "logs:*",
                "application-autoscaling:*",
                "elasticloadbalancing:*",
                "sns:*",
                "cloudwatch:*"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Create policy
aws iam create-policy \
  --policy-name AccuNodeDeploymentPolicy \
  --policy-document file://deployment-policy.json

# Attach policy to user
aws iam attach-user-policy \
  --user-name accunode-deployment \
  --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/AccuNodeDeploymentPolicy

# Create access keys
aws iam create-access-key --user-name accunode-deployment > accunode-credentials.json

echo "✅ IAM user created. Credentials saved in accunode-credentials.json"
echo "⚠️  Configure AWS CLI with these new credentials:"
cat accunode-credentials.json
```

### **1.4 Configure AWS CLI**
```bash
aws configure
# AWS Access Key ID: [Your access key]
# AWS Secret Access Key: [Your secret key]
# Default region name: us-east-1
# Default output format: json

# Test connection
aws sts get-caller-identity
```

---

# **PHASE 2: CORE INFRASTRUCTURE (Day 1-2)**

## **Step 2: Network Infrastructure (VPC)**

### **2.1 Create VPC**
```bash
# Create VPC
VPC_ID=$(aws ec2 create-vpc \
  --cidr-block 10.0.0.0/16 \
  --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=accunode-vpc}]' \
  --query 'Vpc.VpcId' --output text)

echo "VPC ID: $VPC_ID"

# Enable DNS hostnames
aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
```

### **2.2 Create Internet Gateway**
```bash
# Create Internet Gateway
IGW_ID=$(aws ec2 create-internet-gateway \
  --tag-specifications 'ResourceType=internet-gateway,Tags=[{Key=Name,Value=accunode-igw}]' \
  --query 'InternetGateway.InternetGatewayId' --output text)

echo "IGW ID: $IGW_ID"

# Attach to VPC
aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
```

### **2.3 Create Subnets**
```bash
# Public Subnet 1 (us-east-1a)
PUBLIC_SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.1.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=accunode-public-1}]' \
  --query 'Subnet.SubnetId' --output text)

# Public Subnet 2 (us-east-1b)
PUBLIC_SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.2.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=accunode-public-2}]' \
  --query 'Subnet.SubnetId' --output text)

# Private Subnet 1 (us-east-1a)
PRIVATE_SUBNET_1=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.3.0/24 \
  --availability-zone us-east-1a \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=accunode-private-1}]' \
  --query 'Subnet.SubnetId' --output text)

# Private Subnet 2 (us-east-1b)  
PRIVATE_SUBNET_2=$(aws ec2 create-subnet \
  --vpc-id $VPC_ID \
  --cidr-block 10.0.4.0/24 \
  --availability-zone us-east-1b \
  --tag-specifications 'ResourceType=subnet,Tags=[{Key=Name,Value=accunode-private-2}]' \
  --query 'Subnet.SubnetId' --output text)

# Enable auto-assign public IP for public subnets
aws ec2 modify-subnet-attribute --subnet-id $PUBLIC_SUBNET_1 --map-public-ip-on-launch
aws ec2 modify-subnet-attribute --subnet-id $PUBLIC_SUBNET_2 --map-public-ip-on-launch

echo "Public Subnet 1: $PUBLIC_SUBNET_1"
echo "Public Subnet 2: $PUBLIC_SUBNET_2"
echo "Private Subnet 1: $PRIVATE_SUBNET_1"
echo "Private Subnet 2: $PRIVATE_SUBNET_2"
```

### **2.4 Create NAT Gateway**
```bash
# Allocate Elastic IP for NAT Gateway
EIP_ALLOC_ID=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)

# Create NAT Gateway in first public subnet
NAT_GW_ID=$(aws ec2 create-nat-gateway \
  --subnet-id $PUBLIC_SUBNET_1 \
  --allocation-id $EIP_ALLOC_ID \
  --tag-specifications 'ResourceType=nat-gateway,Tags=[{Key=Name,Value=accunode-nat}]' \
  --query 'NatGateway.NatGatewayId' --output text)

echo "NAT Gateway ID: $NAT_GW_ID"

# Wait for NAT Gateway to be available
aws ec2 wait nat-gateway-available --nat-gateway-ids $NAT_GW_ID
```

### **2.5 Create Route Tables**
```bash
# Create Public Route Table
PUBLIC_RT_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=accunode-public-rt}]' \
  --query 'RouteTable.RouteTableId' --output text)

# Create Private Route Table
PRIVATE_RT_ID=$(aws ec2 create-route-table \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=route-table,Tags=[{Key=Name,Value=accunode-private-rt}]' \
  --query 'RouteTable.RouteTableId' --output text)

# Add routes
aws ec2 create-route --route-table-id $PUBLIC_RT_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
aws ec2 create-route --route-table-id $PRIVATE_RT_ID --destination-cidr-block 0.0.0.0/0 --nat-gateway-id $NAT_GW_ID

# Associate subnets with route tables
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_1 --route-table-id $PUBLIC_RT_ID
aws ec2 associate-route-table --subnet-id $PUBLIC_SUBNET_2 --route-table-id $PUBLIC_RT_ID
aws ec2 associate-route-table --subnet-id $PRIVATE_SUBNET_1 --route-table-id $PRIVATE_RT_ID
aws ec2 associate-route-table --subnet-id $PRIVATE_SUBNET_2 --route-table-id $PRIVATE_RT_ID

echo "Public Route Table: $PUBLIC_RT_ID"
echo "Private Route Table: $PRIVATE_RT_ID"
```

## **Step 3: Security Groups**

### **3.1 Create Security Groups**
```bash
# ALB Security Group
ALB_SG_ID=$(aws ec2 create-security-group \
  --group-name accunode-alb-sg \
  --description "Security group for AccuNode Application Load Balancer" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=accunode-alb-sg}]' \
  --query 'GroupId' --output text)

# ECS Security Group
ECS_SG_ID=$(aws ec2 create-security-group \
  --group-name accunode-ecs-sg \
  --description "Security group for AccuNode ECS tasks" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=accunode-ecs-sg}]' \
  --query 'GroupId' --output text)

# RDS Security Group
RDS_SG_ID=$(aws ec2 create-security-group \
  --group-name accunode-rds-sg \
  --description "Security group for AccuNode RDS database" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=accunode-rds-sg}]' \
  --query 'GroupId' --output text)

# Redis Security Group
REDIS_SG_ID=$(aws ec2 create-security-group \
  --group-name accunode-redis-sg \
  --description "Security group for AccuNode ElastiCache Redis" \
  --vpc-id $VPC_ID \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Name,Value=accunode-redis-sg}]' \
  --query 'GroupId' --output text)

echo "ALB SG: $ALB_SG_ID"
echo "ECS SG: $ECS_SG_ID"  
echo "RDS SG: $RDS_SG_ID"
echo "Redis SG: $REDIS_SG_ID"
```

### **3.2 Configure Security Group Rules**
```bash
# ALB Security Group Rules (HTTP/HTTPS from internet)
aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0

aws ec2 authorize-security-group-ingress \
  --group-id $ALB_SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# ECS Security Group Rules (Port 8000 from ALB, HTTPS outbound)
aws ec2 authorize-security-group-ingress \
  --group-id $ECS_SG_ID \
  --protocol tcp \
  --port 8000 \
  --source-group $ALB_SG_ID

aws ec2 authorize-security-group-egress \
  --group-id $ECS_SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# RDS Security Group Rules (PostgreSQL from ECS only)
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $ECS_SG_ID

# Redis Security Group Rules (Redis from ECS only)
aws ec2 authorize-security-group-ingress \
  --group-id $REDIS_SG_ID \
  --protocol tcp \
  --port 6379 \
  --source-group $ECS_SG_ID
```

---

# **PHASE 3: CRITICAL DATABASES (Day 2)**

## **Step 4: PostgreSQL Database (RDS)**

### **4.1 Create DB Subnet Group**
```bash
# Create DB Subnet Group
aws rds create-db-subnet-group \
  --db-subnet-group-name accunode-db-subnet-group \
  --db-subnet-group-description "Subnet group for AccuNode database" \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2 \
  --tags Key=Name,Value=accunode-db-subnet-group
```

### **4.2 Create RDS PostgreSQL Instance**
```bash
# Generate database password
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-20)
echo "Database Password: $DB_PASSWORD" > db_credentials.txt

# Create RDS instance
aws rds create-db-instance \
  --db-instance-identifier accunode-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 15.4 \
  --master-username dbadmin \
  --master-user-password "$DB_PASSWORD" \
  --allocated-storage 20 \
  --storage-type gp2 \
  --vpc-security-group-ids $RDS_SG_ID \
  --db-subnet-group-name accunode-db-subnet-group \
  --backup-retention-period 7 \
  --no-multi-az \
  --storage-encrypted \
  --no-publicly-accessible \
  --tags Key=Name,Value=accunode-database

echo "RDS instance creation initiated. This will take 5-10 minutes."
echo "Password saved in db_credentials.txt"

# Wait for RDS to be available (optional - takes 5-10 minutes)
# aws rds wait db-instance-available --db-instance-identifier accunode-db
```

### **4.3 Get Database Endpoint (Run after RDS is ready)**
```bash
# Get RDS endpoint (run this after database is available)
DB_ENDPOINT=$(aws rds describe-db-instances \
  --db-instance-identifier accunode-db \
  --query 'DBInstances[0].Endpoint.Address' --output text)

echo "Database Endpoint: $DB_ENDPOINT"

# Create database URL
DB_URL="postgresql://dbadmin:$DB_PASSWORD@$DB_ENDPOINT:5432/postgres"
echo "Database URL: $DB_URL"
```

## **Step 5: Redis Cache (ElastiCache)**

### **5.1 Create Redis Subnet Group**
```bash
# Create Redis Subnet Group
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name accunode-redis-subnet-group \
  --cache-subnet-group-description "Subnet group for AccuNode Redis" \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2
```

### **5.2 Create Redis Cluster**
```bash
# Create Redis cluster
aws elasticache create-cache-cluster \
  --cache-cluster-id accunode-redis \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --num-cache-nodes 1 \
  --cache-subnet-group-name accunode-redis-subnet-group \
  --security-group-ids $REDIS_SG_ID \
  --tags Key=Name,Value=accunode-redis

echo "Redis cluster creation initiated. This will take 3-5 minutes."

# Wait for Redis to be available (optional)
# aws elasticache wait cache-cluster-available --cache-cluster-id accunode-redis
```

### **5.3 Get Redis Endpoint (Run after Redis is ready)**
```bash
# Get Redis endpoint (run this after cluster is available)
REDIS_ENDPOINT=$(aws elasticache describe-cache-clusters \
  --cache-cluster-id accunode-redis \
  --show-cache-node-info \
  --query 'CacheClusters[0].CacheNodes[0].Endpoint.Address' --output text)

echo "Redis Endpoint: $REDIS_ENDPOINT"

# Create Redis URL
REDIS_URL="redis://$REDIS_ENDPOINT:6379/0"
echo "Redis URL: $REDIS_URL"
```

---

# **PHASE 4: APPLICATION STORAGE (Day 2)**

## **Step 6: S3 Bucket for ML Models**

### **6.1 Create S3 Bucket**
```bash
# Create unique bucket name
BUCKET_NAME="accunode-ml-models-prod-$(date +%s)"

# Create S3 bucket
aws s3 mb s3://$BUCKET_NAME --region us-east-1

echo "S3 Bucket: $BUCKET_NAME"
```

### **6.2 Upload ML Models**
```bash
# Navigate to your project directory (update path as needed)
cd /Users/nikhil/Downloads/pranit/work/final/default-rate/backend

# Upload ML models to S3
aws s3 cp app/models/ s3://$BUCKET_NAME/models/ --recursive

# Verify upload
aws s3 ls s3://$BUCKET_NAME/models/

echo "ML models uploaded to S3"
```

### **6.3 Set Bucket Policy (Private)**
```bash
# Create bucket policy for ECS access only
cat > bucket-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "ECSTaskAccess",
            "Effect": "Allow",
            "Principal": {
                "AWS": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):root"
            },
            "Action": [
                "s3:GetObject",
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
        }
    ]
}
EOF

# Apply bucket policy
aws s3api put-bucket-policy --bucket $BUCKET_NAME --policy file://bucket-policy.json
```

---

# **PHASE 5: SECRETS MANAGEMENT (Day 2)**

## **Step 7: Store Secrets in Parameter Store**

### **7.1 Generate Application Secrets**
```bash
# Generate secure secrets
SECRET_KEY=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)

echo "Generated secrets:"
echo "SECRET_KEY: $SECRET_KEY"
echo "JWT_SECRET: $JWT_SECRET"
```

### **7.2 Store Secrets in Parameter Store**
```bash
# Store database URL
aws ssm put-parameter \
  --name "/accunode/database-url" \
  --value "$DB_URL" \
  --type "SecureString" \
  --description "AccuNode database connection URL"

# Store Redis URL  
aws ssm put-parameter \
  --name "/accunode/redis-url" \
  --value "$REDIS_URL" \
  --type "SecureString" \
  --description "AccuNode Redis connection URL"

# Store Secret Key
aws ssm put-parameter \
  --name "/accunode/secret-key" \
  --value "$SECRET_KEY" \
  --type "SecureString" \
  --description "AccuNode application secret key"

# Store JWT Secret
aws ssm put-parameter \
  --name "/accunode/jwt-secret" \
  --value "$JWT_SECRET" \
  --type "SecureString" \
  --description "AccuNode JWT signing secret"

# Store S3 bucket name
aws ssm put-parameter \
  --name "/accunode/s3-models-bucket" \
  --value "$BUCKET_NAME" \
  --type "String" \
  --description "AccuNode S3 bucket for ML models"

echo "All secrets stored in Parameter Store"
```

---

# **PHASE 6: CONTAINER SETUP (Day 3)**

## **Step 8: Container Registry (ECR)**

### **8.1 Create ECR Repository**
```bash
# Create ECR repository
aws ecr create-repository --repository-name accunode-app --region us-east-1

# Get login token for Docker
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com

# Get repository URI
ECR_URI=$(aws ecr describe-repositories --repository-names accunode-app --query 'repositories[0].repositoryUri' --output text)
echo "ECR Repository URI: $ECR_URI"
```

### **8.2 Prepare Application for AWS (Code Changes)**
```bash
# Navigate to your project
cd /Users/nikhil/Downloads/pranit/work/final/default-rate/backend

# Ensure you're on prod branch
git checkout prod
git pull origin prod
```

Now you need to update your code for AWS S3 model loading. Create this file:

### **8.3 Update ML Service for S3 (Critical)**
Create/update `app/services/aws_ml_service.py`:
```python
import boto3
import pickle
import os
import logging
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class AccuNodeMLServiceMixin:
    """AWS S3 integration for AccuNode ML models"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
        self.bucket_name = os.getenv('S3_MODELS_BUCKET', 'accunode-ml-models-prod')
        self.model_cache = {}
        
    def load_model_from_s3(self, model_path: str):
        """Load ML model from S3 with local caching"""
        if model_path in self.model_cache:
            return self.model_cache[model_path]
            
        try:
            # Download model from S3
            s3_key = f"models/{model_path}"
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=s3_key)
            model_data = response['Body'].read()
            
            # Load model from bytes
            model = pickle.loads(model_data)
            
            # Cache the model
            self.model_cache[model_path] = model
            
            logger.info(f"✅ Loaded model {model_path} from S3")
            return model
            
        except Exception as e:
            logger.error(f"❌ Failed to load model {model_path} from S3: {e}")
            raise e
```

### **8.4 Build and Push Docker Image**
```bash
# Build Docker image
docker build -t accunode-app .

# Tag for ECR
docker tag accunode-app:latest $ECR_URI:latest
docker tag accunode-app:latest $ECR_URI:$(git rev-parse --short HEAD)

# Push to ECR
docker push $ECR_URI:latest
docker push $ECR_URI:$(git rev-parse --short HEAD)

echo "Docker image pushed to ECR: $ECR_URI"
```

---

# **PHASE 7: ECS SETUP (Day 3)**

## **Step 9: ECS Cluster and IAM Roles**

### **9.1 Create IAM Roles**
```bash
# Create ECS Task Execution Role
cat > ecs-task-execution-role-trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "ecs-tasks.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the execution role
aws iam create-role \
  --role-name ecsTaskExecutionRole \
  --assume-role-policy-document file://ecs-task-execution-role-trust-policy.json

# Attach AWS managed policy
aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

# Create custom policy for Parameter Store access
cat > ecs-parameter-store-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameters",
        "ssm:GetParameter"
      ],
      "Resource": "arn:aws:ssm:us-east-1:$(aws sts get-caller-identity --query Account --output text):parameter/accunode/*"
    }
  ]
}
EOF

# Create and attach Parameter Store policy
aws iam create-policy \
  --policy-name ECSParameterStoreAccess \
  --policy-document file://ecs-parameter-store-policy.json

aws iam attach-role-policy \
  --role-name ecsTaskExecutionRole \
  --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/ECSParameterStoreAccess
```

### **9.2 Create ECS Task Role (for S3 access)**
```bash
# Create ECS Task Role for application permissions
aws iam create-role \
  --role-name ecsTaskRole \
  --assume-role-policy-document file://ecs-task-execution-role-trust-policy.json

# Create S3 access policy
cat > ecs-s3-access-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::$BUCKET_NAME/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket"
      ],
      "Resource": "arn:aws:s3:::$BUCKET_NAME"
    }
  ]
}
EOF

# Create and attach S3 policy
aws iam create-policy \
  --policy-name ECSS3Access \
  --policy-document file://ecs-s3-access-policy.json

aws iam attach-role-policy \
  --role-name ecsTaskRole \
  --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/ECSS3Access
```

### **9.3 Create ECS Cluster**
```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name accunode-cluster

# Create CloudWatch Log Group
aws logs create-log-group --log-group-name /ecs/accunode

echo "ECS cluster created: accunode-cluster"
```

## **Step 10: ECS Task Definition**

### **10.1 Create Task Definition**
```bash
# Create task definition file
cat > task-definition.json << EOF
{
  "family": "accunode-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "accunode-app",
      "image": "$ECR_URI:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        },
        {
          "name": "AWS_DEFAULT_REGION",
          "value": "us-east-1"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "/accunode/database-url"
        },
        {
          "name": "REDIS_URL", 
          "valueFrom": "/accunode/redis-url"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "/accunode/secret-key"
        },
        {
          "name": "JWT_SECRET",
          "valueFrom": "/accunode/jwt-secret"
        },
        {
          "name": "S3_MODELS_BUCKET",
          "valueFrom": "/accunode/s3-models-bucket"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/accunode",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
EOF

# Register task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

echo "Task definition registered"
```

---

# **PHASE 8: LOAD BALANCER (Day 3)**

## **Step 11: Application Load Balancer**

### **11.1 Create Target Group**
```bash
# Create target group
TARGET_GROUP_ARN=$(aws elbv2 create-target-group \
  --name accunode-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --target-type ip \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --health-check-timeout-seconds 10 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 3 \
  --query 'TargetGroups[0].TargetGroupArn' --output text)

echo "Target Group ARN: $TARGET_GROUP_ARN"
```

### **11.2 Create Application Load Balancer**
```bash
# Create ALB
ALB_ARN=$(aws elbv2 create-load-balancer \
  --name accunode-alb \
  --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 \
  --security-groups $ALB_SG_ID \
  --query 'LoadBalancers[0].LoadBalancerArn' --output text)

# Get ALB DNS name
ALB_DNS=$(aws elbv2 describe-load-balancers \
  --load-balancer-arns $ALB_ARN \
  --query 'LoadBalancers[0].DNSName' --output text)

echo "ALB ARN: $ALB_ARN"
echo "ALB DNS: $ALB_DNS"
```

### **11.3 Create HTTP Listener (Temporary)**
```bash
# Create HTTP listener (we'll add HTTPS later)
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN

echo "HTTP listener created (temporary)"
```

---

# **PHASE 9: ECS SERVICE DEPLOYMENT (Day 4)**

## **Step 12: Deploy ECS Service**

### **12.1 Create ECS Service**
```bash
# Create service configuration
cat > service-definition.json << EOF
{
  "serviceName": "accunode-service",
  "cluster": "accunode-cluster", 
  "taskDefinition": "accunode-task",
  "desiredCount": 1,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["$PRIVATE_SUBNET_1", "$PRIVATE_SUBNET_2"],
      "securityGroups": ["$ECS_SG_ID"],
      "assignPublicIp": "DISABLED"
    }
  },
  "loadBalancers": [
    {
      "targetGroupArn": "$TARGET_GROUP_ARN",
      "containerName": "accunode-app",
      "containerPort": 8000
    }
  ],
  "healthCheckGracePeriodSeconds": 120
}
EOF

# Create ECS service
aws ecs create-service --cli-input-json file://service-definition.json

echo "ECS service created. Waiting for deployment..."

# Wait for service to become stable (this takes 3-5 minutes)
aws ecs wait services-stable --cluster accunode-cluster --services accunode-service

echo "✅ ECS service is now running!"
```

### **12.2 Verify Deployment**
```bash
# Check service status
aws ecs describe-services --cluster accunode-cluster --services accunode-service

# Test health endpoint
echo "Testing application health..."
curl -f http://$ALB_DNS/health

echo "✅ Application is responding!"
```

---

# **PHASE 10: SSL & DOMAIN (Day 4)**

## **Step 13: SSL Certificate & HTTPS**

### **13.1 SSL Certificate Setup (CLI-Only)**
```bash
# Check if SSL should be skipped
if [ "$DOMAIN_NAME" = "skip-ssl" ]; then
    echo "🌐 SKIPPING SSL SETUP - Using HTTP only"
    echo "✅ Your AccuNode app will be accessible at: http://$ALB_DNS"
    echo "💰 Cost savings: No domain/certificate costs"
    echo "📝 You can add SSL later by:"
    echo "   1. Buy/configure a domain"
    echo "   2. Request SSL certificate"
    echo "   3. Update ALB listeners"
    echo ""
    echo "🎯 CONTINUING WITHOUT SSL..."
    
else
    echo "🔒 Setting up SSL certificate for domain: $DOMAIN_NAME"
    
    # Request certificate (requires domain validation)
    CERT_ARN=$(aws acm request-certificate \
      --domain-name $DOMAIN_NAME \
      --domain-name "www.$DOMAIN_NAME" \
      --validation-method DNS \
      --query 'CertificateArn' --output text)

    echo "Certificate ARN: $CERT_ARN"

    # Get DNS validation records via CLI
    echo "📋 DNS Validation Records (add these to your DNS provider):"
    aws acm describe-certificate \
      --certificate-arn $CERT_ARN \
      --query 'Certificate.DomainValidationOptions[*].[DomainName,ResourceRecord.Name,ResourceRecord.Type,ResourceRecord.Value]' \
      --output table

    echo ""
    echo "🎯 CLI Commands to add DNS records (example for Route 53):"
    echo "For each domain, run:"
    echo "aws route53 change-resource-record-sets --hosted-zone-id YOUR_ZONE_ID --change-batch file://dns-validation.json"

    # Create example DNS validation file
    cat > dns-validation-example.json << EOF
{
  "Comment": "SSL Certificate Validation for $DOMAIN_NAME",
  "Changes": [
    {
      "Action": "CREATE",
      "ResourceRecordSet": {
        "Name": "_VALIDATION_NAME_FROM_TABLE_ABOVE",
        "Type": "CNAME",
        "TTL": 300,
        "ResourceRecords": [
          {
            "Value": "_VALIDATION_VALUE_FROM_TABLE_ABOVE"
          }
        ]
      }
    }
  ]
}
EOF

    echo "📝 DNS validation file created: dns-validation-example.json"
    echo "⚠️  Update with actual values from the table above and run the Route53 command"
fi
```

### **13.2 Configure HTTPS Listener (If SSL enabled)**
```bash
if [ "$DOMAIN_NAME" = "skip-ssl" ]; then
    echo "🌐 SKIPPING HTTPS LISTENER - Using HTTP only"
    echo "✅ AccuNode is accessible at: http://$ALB_DNS"
    echo "🔧 HTTP listener is already configured from Step 11.3"
    
else
    echo "🔒 Setting up HTTPS listener for $DOMAIN_NAME..."
    
    # Wait for certificate validation first
    echo "⏳ Waiting for SSL certificate validation..."
    echo "⚠️  Make sure you've added the DNS validation records!"
    echo "   Check certificate status: aws acm describe-certificate --certificate-arn $CERT_ARN"
    echo ""
    echo "📝 Press Enter when certificate is validated, or Ctrl+C to skip and setup later..."
    read -p "Certificate validated? (press Enter to continue): "
    
    # Create HTTPS listener (run after certificate is validated)
    aws elbv2 create-listener \
      --load-balancer-arn $ALB_ARN \
      --protocol HTTPS \
      --port 443 \
      --certificates CertificateArn=$CERT_ARN \
      --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN

    # Modify HTTP listener to redirect to HTTPS
    HTTP_LISTENER_ARN=$(aws elbv2 describe-listeners --load-balancer-arn $ALB_ARN --query 'Listeners[?Port==`80`].ListenerArn' --output text)

    aws elbv2 modify-listener \
      --listener-arn $HTTP_LISTENER_ARN \
      --default-actions Type=redirect,RedirectConfig='{Protocol=HTTPS,Port=443,StatusCode=HTTP_301}'

    echo "✅ HTTPS listener created, HTTP now redirects to HTTPS"
    echo "🌐 AccuNode is now accessible at: https://$DOMAIN_NAME"
fi
```

---

# **PHASE 11: AUTO-SCALING (Day 4)**

## **Step 14: Configure Auto-Scaling**

### **14.1 Create Auto-Scaling Target**
```bash
# Register ECS service as scalable target
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/accunode-cluster/accunode-service \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 1 \
  --max-capacity 5
```

### **14.2 Create Scaling Policy**
```bash
# Create CPU-based scaling policy
SCALE_UP_POLICY_ARN=$(aws application-autoscaling put-scaling-policy \
  --service-namespace ecs \
  --resource-id service/accunode-cluster/accunode-service \
  --scalable-dimension ecs:service:DesiredCount \
  --policy-name accunode-cpu-scaling \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ECSServiceAverageCPUUtilization"
    },
    "ScaleOutCooldown": 300,
    "ScaleInCooldown": 300
  }' \
  --query 'PolicyARN' --output text)

echo "Auto-scaling policy created: $SCALE_UP_POLICY_ARN"
```

---

# **PHASE 12: MONITORING (Day 4)**

## **Step 15: Basic CloudWatch Alarms**

### **15.1 Create SNS Topic for Alerts**
```bash
# Create SNS topic for alerts
TOPIC_ARN=$(aws sns create-topic --name accunode-alerts --query 'TopicArn' --output text)

# Subscribe your email (replace with your email)
YOUR_EMAIL="your-email@example.com"
aws sns subscribe --topic-arn $TOPIC_ARN --protocol email --notification-endpoint $YOUR_EMAIL

echo "SNS topic created: $TOPIC_ARN"
echo "Check your email to confirm subscription"
```

### **15.2 Create CloudWatch Alarms**
```bash
# ECS Service Health Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "AccuNode-ECS-ServiceHealth" \
  --alarm-description "Alert when AccuNode ECS service has no running tasks" \
  --metric-name RunningTaskCount \
  --namespace AWS/ECS \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions $TOPIC_ARN \
  --dimensions Name=ServiceName,Value=accunode-service Name=ClusterName,Value=accunode-cluster

# ALB Target Health Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "AccuNode-ALB-TargetHealth" \
  --alarm-description "Alert when AccuNode ALB has no healthy targets" \
  --metric-name HealthyHostCount \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 60 \
  --threshold 1 \
  --comparison-operator LessThanThreshold \
  --evaluation-periods 2 \
  --alarm-actions $TOPIC_ARN \
  --dimensions Name=TargetGroup,Value=$(echo $TARGET_GROUP_ARN | sed 's/.*\///') Name=LoadBalancer,Value=$(echo $ALB_ARN | sed 's/.*loadbalancer\///')

echo "CloudWatch alarms created"
```

---

# **PHASE 13: DATA MIGRATION (Day 5)**

## **Step 16: Migrate Existing Data**

### **16.1 Export Current Database**
```bash
# From your current environment, export data
# Replace with your current database URL
CURRENT_DB_URL="your-current-database-url"

# Export data
pg_dump "$CURRENT_DB_URL" > production_backup.sql

echo "Database exported to production_backup.sql"
```

### **16.2 Import Data to AWS RDS**
```bash
# Wait for RDS to be fully available
aws rds wait db-instance-available --db-instance-identifier accunode-db

# Get database URL from Parameter Store
AWS_DB_URL=$(aws ssm get-parameter --name "/accunode/database-url" --with-decryption --query 'Parameter.Value' --output text)

# Import data
psql "$AWS_DB_URL" < production_backup.sql

echo "✅ Data migration completed"
```

---

# **PHASE 14: CI/CD PIPELINE (Day 5)**

## **Step 17: GitHub Actions Setup**

### **17.1 Add GitHub Secrets**
```bash
# Add GitHub secrets via CLI (requires GitHub CLI)
# Install GitHub CLI: brew install gh
# Login: gh auth login

# Add secrets via CLI
gh secret set AWS_ACCESS_KEY_ID --body "$(cat accunode-credentials.json | jq -r '.AccessKey.AccessKeyId')"
gh secret set AWS_SECRET_ACCESS_KEY --body "$(cat accunode-credentials.json | jq -r '.AccessKey.SecretAccessKey')"
gh secret set AWS_ACCOUNT_ID --body "$(aws sts get-caller-identity --query Account --output text)"
gh secret set ECR_REPOSITORY --body "accunode-app"
gh secret set ECS_CLUSTER --body "accunode-cluster"
gh secret set ECS_SERVICE --body "accunode-service"

echo "✅ GitHub secrets added via CLI"
```

### **17.2 Create GitHub Actions Workflow**
Create `.github/workflows/deploy-prod.yml` in your repository:

```yaml
name: Deploy to AWS Production

on:
  push:
    branches: [prod]

env:
  AWS_REGION: us-east-1
  ECR_REPOSITORY: accunode-app
  ECS_CLUSTER: accunode-cluster
  ECS_SERVICE: accunode-service

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}

    - name: Login to Amazon ECR
      id: login-ecr
      uses: aws-actions/amazon-ecr-login@v1

    - name: Build, tag, and push image to Amazon ECR
      id: build-image
      env:
        ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
        IMAGE_TAG: ${{ github.sha }}
      run: |
        docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
        docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
        docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
        echo "image=$ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG" >> $GITHUB_OUTPUT

    - name: Deploy to Amazon ECS
      run: |
        aws ecs update-service \
          --cluster $ECS_CLUSTER \
          --service $ECS_SERVICE \
          --force-new-deployment
        
        aws ecs wait services-stable \
          --cluster $ECS_CLUSTER \
          --services $ECS_SERVICE

    - name: Health Check
      run: |
        sleep 60
        # Add your health check URL here
        curl -f https://yourdomain.com/health || exit 1
```

---

# **PHASE 15: FINAL TESTING & GO-LIVE (Day 5)**

## **Step 18: Final Verification**

### **18.1 Complete System Test**
```bash
# Test all major endpoints
ALB_URL="http://$ALB_DNS"  # Use HTTPS if certificate is ready

# Health check
curl -f $ALB_URL/health

# API documentation
curl -f $ALB_URL/docs

# Test authentication endpoint
curl -X POST $ALB_URL/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","full_name":"Test User"}'

echo "✅ System tests completed"
```

### **18.2 Performance Test**
```bash
# Install Apache Bench (if not installed)
# brew install apache2

# Simple load test
ab -n 100 -c 10 $ALB_URL/health

echo "Performance test completed"
```

### **18.3 Monitor Logs**
```bash
# Check ECS service logs
aws logs describe-log-streams --log-group-name /ecs/default-rate

# Tail logs in real-time (optional)
# aws logs tail /ecs/default-rate --follow
```

---

# **🎉 ACCUNODE DEPLOYMENT COMPLETE!**

## **Summary of What You've Built:**

✅ **Complete CLI-only deployment process**  
✅ **VPC with public/private subnets (accunode-vpc)**  
✅ **RDS PostgreSQL database (accunode-db)**  
✅ **ElastiCache Redis cluster (accunode-redis)**  
✅ **S3 bucket with ML models (accunode-ml-models-prod)**  
✅ **ECS Fargate service with auto-scaling (accunode-cluster/accunode-service)**  
✅ **Application Load Balancer with SSL (accunode-alb)**  
✅ **CloudWatch monitoring and alerts**  
✅ **GitHub Actions CI/CD pipeline**  
✅ **Secure secrets management (/accunode/ parameters)**

## **Access Your AccuNode Application:**
```bash
if [ "$DOMAIN_NAME" = "skip-ssl" ]; then
    echo "🌐 AccuNode Application URLs:"
    echo "Main App: http://$ALB_DNS"
    echo "API Docs: http://$ALB_DNS/docs" 
    echo "Health Check: http://$ALB_DNS/health"
    echo "Admin Panel: http://$ALB_DNS/admin (if enabled)"
else
    echo "🌐 AccuNode Application URLs:"
    echo "Main App: https://$DOMAIN_NAME"
    echo "API Docs: https://$DOMAIN_NAME/docs"
    echo "Health Check: https://$DOMAIN_NAME/health" 
    echo "HTTP Redirect: http://$DOMAIN_NAME → https://$DOMAIN_NAME"
fi
```

## **CLI Commands for Monitoring:**
```bash
# Check all resources
aws ecs describe-services --cluster accunode-cluster --services accunode-service
aws rds describe-db-instances --db-instance-identifier accunode-db
aws elasticache describe-cache-clusters --cache-cluster-id accunode-redis
aws s3 ls s3://$BUCKET_NAME/

# Check logs
aws logs tail /ecs/accunode --follow

# Check costs
aws ce get-cost-and-usage --time-period Start=2025-10-01,End=2025-10-31 --granularity MONTHLY --metrics BlendedCost
```

## **Estimated Monthly Cost:**
- **Year 1 (Free Tier)**: ~$104/month
- **Year 2+**: ~$119/month
- **Optimized**: ~$55-85/month (with reserved instances)

## **Complete CLI Deployment Files Created:**
- `accunode-deployment-config.env` - Configuration
- `deployment-policy.json` - IAM policies  
- `task-definition.json` - ECS task definition
- `service-definition.json` - ECS service definition
- `dns-validation-example.json` - SSL validation
- `.github/workflows/deploy-prod.yml` - CI/CD pipeline

## **Next Steps:**
1. **Validate SSL certificate** via CLI DNS commands shown above
2. **Set up custom domain** pointing to ALB DNS
3. **Test all AccuNode features** via API endpoints
4. **Monitor costs** using CLI commands above
5. **Scale as needed** using ECS auto-scaling

**🚀 AccuNode is now running on production-grade AWS infrastructure - completely deployed via CLI!**
