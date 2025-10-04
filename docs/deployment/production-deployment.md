# Production Deployment Guide

Complete guide for deploying AccuNode to AWS production environment.

## Overview

This guide covers the complete production deployment of AccuNode, including infrastructure setup, application deployment, and post-deployment verification.

> CI/CD note: Current GitHub Actions workflow deploys on pushes to `prod` only. Staging is not auto-deployed.

## Prerequisites

### Required Tools
- AWS CLI v2.x configured with appropriate permissions
- Terraform v1.5+ for infrastructure as code
- Docker for local testing
- Git for source code management

### AWS Permissions Required
- EC2 (ECS, Security Groups, Load Balancers)
- RDS (PostgreSQL database management)
- ElastiCache (Redis cache management)
- Route53 (DNS management)
- Certificate Manager (SSL certificates)
- CloudWatch (Logging and monitoring)
- Parameter Store (Configuration management)

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    PRODUCTION DEPLOYMENT                    │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Infrastructure Layer (Terraform)                         │
│  ├── VPC, Subnets, Security Groups                        │
│  ├── RDS PostgreSQL                                       │
│  ├── ElastiCache Redis                                    │
│  ├── Application Load Balancer                            │
│  └── ECS Fargate Cluster                                  │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Application Layer (GitHub Actions)                       │
│  ├── Docker Image Build                                   │
│  ├── ECR Image Push                                       │
│  ├── ECS Service Update                                   │
│  └── Health Check Verification                            │
└─────────────────────────────────────────────────────────────┘
```

## Step 1: Infrastructure Deployment

### 1.1 Terraform Configuration

Navigate to the infrastructure directory and initialize Terraform:

```bash
cd deployment/aws/terraform
terraform init
```

### 1.2 Configure Environment Variables

Create `terraform.tfvars`:

```hcl
# Environment Configuration
environment = "production"
region      = "us-east-1"

# Network Configuration
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["us-east-1a", "us-east-1b"]
private_subnet_cidrs = ["10.0.1.0/24", "10.0.2.0/24"]
public_subnet_cidrs  = ["10.0.101.0/24", "10.0.102.0/24"]

# Domain Configuration
domain_name    = "accunode.com"
api_subdomain  = "api"

# Database Configuration
db_instance_class    = "db.t3.medium"
db_allocated_storage = 100
db_max_allocated_storage = 1000
db_backup_retention_period = 7

# Redis Configuration
redis_node_type = "cache.t3.micro"
redis_num_cache_nodes = 1

# ECS Configuration
app_cpu    = 512
app_memory = 1024
min_capacity = 2
max_capacity = 10

# Admin Access
admin_ip_addresses = [
  "YOUR_OFFICE_IP/32",
  "YOUR_HOME_IP/32"
]
```

### 1.3 Deploy Infrastructure

```bash
# Plan deployment
terraform plan -out=production.plan

# Review the plan carefully
terraform show production.plan

# Apply infrastructure
terraform apply production.plan
```

### 1.4 Verify Infrastructure

```bash
# Check VPC creation
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=AccuNode VPC"

# Verify RDS instance
aws rds describe-db-instances --db-instance-identifier accunode-prod-db

# Check ECS cluster
aws ecs describe-clusters --clusters accunode-production
```

## Step 2: Application Configuration

### 2.1 Parameter Store Setup

Configure application parameters in AWS Parameter Store:

```bash
# Database configuration
aws ssm put-parameter \
  --name "/accunode/production/database/host" \
  --value "accunode-prod-db.xxxxxxxxx.us-east-1.rds.amazonaws.com" \
  --type "String"

aws ssm put-parameter \
  --name "/accunode/production/database/name" \
  --value "accunode_prod" \
  --type "String"

aws ssm put-parameter \
  --name "/accunode/production/database/username" \
  --value "accunode_user" \
  --type "String"

aws ssm put-parameter \
  --name "/accunode/production/database/password" \
  --value "SECURE_DATABASE_PASSWORD" \
  --type "SecureString"

# Redis configuration
aws ssm put-parameter \
  --name "/accunode/production/redis/host" \
  --value "accunode-redis.xxxxxx.cache.amazonaws.com" \
  --type "String"

# JWT configuration
aws ssm put-parameter \
  --name "/accunode/production/jwt/secret" \
  --value "SECURE_JWT_SECRET_KEY" \
  --type "SecureString"

# Application configuration
aws ssm put-parameter \
  --name "/accunode/production/app/environment" \
  --value "production" \
  --type "String"

aws ssm put-parameter \
  --name "/accunode/production/app/debug" \
  --value "false" \
  --type "String"
```

### 2.2 ECR Repository Setup

Create ECR repository for Docker images:

```bash
# Create repository (matches CI env ECR_REPOSITORY)
aws ecr create-repository --repository-name accunode

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

## Step 3: Application Deployment

### 3.1 GitHub Actions Setup

Configure GitHub repository secrets for automated deployment:

```bash
# AWS credentials
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1

# ECR configuration
ECR_REGISTRY=ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
ECR_REPOSITORY=accunode/api

# ECS configuration
ECS_CLUSTER=accunode-production
ECS_SERVICE=accunode-api-service
ECS_TASK_DEFINITION=accunode-api-task
```

### 3.2 Build and Deploy

Push code to trigger automated deployment:

```bash
# Create production release
git checkout prod
git merge prod-dev
git tag -a v2.0.0 -m "Production release v2.0.0"
git push origin prod
git push origin v2.0.0
```

The GitHub Actions workflow will:
1. Build Docker image (repository: accunode; tags: prod-<short_sha>, latest, prod)
2. Push to ECR
3. Update ECS task definition
4. Deploy to ECS service
5. Verify health checks

### 3.3 Manual Deployment (if needed)

If automated deployment fails, deploy manually:

```bash
# Build and push image
docker build -t accunode/api .
docker tag accunode/api:latest ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/accunode/api:latest
docker push ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/accunode/api:latest

# Update ECS service
aws ecs update-service \
  --cluster accunode-production \
  --service accunode-api-service \
  --force-new-deployment
```

## Step 4: Database Setup

### 4.1 Database Migration

Connect to RDS via bastion host and setup database:

```bash
# Connect to bastion
ssh -i bastion-key.pem ec2-user@bastion.accunode.com

# Connect to RDS from bastion
psql -h accunode-prod-db.xxxxxxxxx.us-east-1.rds.amazonaws.com -U accunode_user -d accunode_prod

# Run initial setup
\i /path/to/init_db.sql
```

### 4.2 Database Schema Creation

Execute database initialization:

```sql
-- Create database and user
CREATE DATABASE accunode_prod;
CREATE USER accunode_user WITH ENCRYPTED PASSWORD 'SECURE_PASSWORD';
GRANT ALL PRIVILEGES ON DATABASE accunode_prod TO accunode_user;

-- Connect to application database
\c accunode_prod;

-- Create schema (this will be done by SQLAlchemy migrations)
-- Tables will be created automatically by the application
```

## Step 5: SSL Certificate Setup

### 5.1 Request Certificate

```bash
# Request SSL certificate through ACM
aws acm request-certificate \
  --domain-name api.accunode.com \
  --subject-alternative-names "*.accunode.com" \
  --validation-method DNS \
  --region us-east-1
```

### 5.2 DNS Validation

Add DNS validation records to Route53:

```bash
# Get certificate validation records
aws acm describe-certificate --certificate-arn arn:aws:acm:us-east-1:ACCOUNT:certificate/CERT-ID

# Add validation records to Route53 (usually automated with Terraform)
```

## Step 6: Post-Deployment Verification

### 6.1 Health Checks

Verify application health:

```bash
# Check ECS service status
aws ecs describe-services --cluster accunode-production --services accunode-api-service

# Test health endpoint
curl -k https://api.accunode.com/health

# Expected response:
{
  "status": "healthy",
  "service": "accunode-api",
  "version": "2.0.0",
  "timestamp": "2025-10-05T12:00:00Z"
}
```

### 6.2 API Testing

Test core API functionality:

```bash
# Test authentication
curl -X POST https://api.accunode.com/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePassword123",
    "full_name": "Test User"
  }'

# Test ML prediction
curl -X POST https://api.accunode.com/api/v1/predictions/annual \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "company_symbol": "TEST",
    "company_name": "Test Company",
    "market_cap": 1000000,
    "sector": "Technology",
    "reporting_year": "2024",
    "long_term_debt_to_total_capital": 25.0,
    "total_debt_to_ebitda": 2.5,
    "net_income_margin": 10.0,
    "ebit_to_interest_expense": 15.0,
    "return_on_assets": 8.0
  }'
```

### 6.3 Monitoring Setup

Verify CloudWatch metrics:

```bash
# Check ECS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=accunode-api-service \
  --start-time 2025-10-05T00:00:00Z \
  --end-time 2025-10-05T23:59:59Z \
  --period 300 \
  --statistics Average

# Check ALB metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ApplicationELB \
  --metric-name RequestCount \
  --dimensions Name=LoadBalancer,Value=app/accunode-alb/xxxxxxxxxxxxx \
  --start-time 2025-10-05T00:00:00Z \
  --end-time 2025-10-05T23:59:59Z \
  --period 300 \
  --statistics Sum
```

## Step 7: DNS Configuration

### 7.1 Route53 Setup

Configure DNS records:

```bash
# Create hosted zone (if not exists)
aws route53 create-hosted-zone --name accunode.com --caller-reference $(date +%s)

# Create A record for API
aws route53 change-resource-record-sets --hosted-zone-id Z1234567890ABC --change-batch file://api-dns-record.json
```

### 7.2 DNS Record Configuration

Create `api-dns-record.json`:

```json
{
  "Changes": [{
    "Action": "CREATE",
    "ResourceRecordSet": {
      "Name": "api.accunode.com",
      "Type": "A",
      "AliasTarget": {
        "DNSName": "accunode-alb-1234567890.us-east-1.elb.amazonaws.com",
        "EvaluateTargetHealth": true,
        "HostedZoneId": "Z35SXDOTRQ7X7K"
      }
    }
  }]
}
```

## Production Environment Variables

The application uses these environment variables in production:

```bash
# Application Configuration
APP_ENVIRONMENT=production
APP_DEBUG=false
APP_LOG_LEVEL=info

# Database Configuration (from Parameter Store)
DATABASE_HOST=/accunode/production/database/host
DATABASE_NAME=/accunode/production/database/name
DATABASE_USER=/accunode/production/database/username  
DATABASE_PASSWORD=/accunode/production/database/password

# Redis Configuration (from Parameter Store)
REDIS_HOST=/accunode/production/redis/host
REDIS_PORT=6379

# JWT Configuration (from Parameter Store)
JWT_SECRET_KEY=/accunode/production/jwt/secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# ML Model Configuration
ML_MODEL_PATH=/app/models/
ANNUAL_MODEL_FILE=annual_logistic_model.pkl
QUARTERLY_MODEL_FILE=quarterly_lgb_model.pkl
```

## Security Considerations

### 1. Network Security
- All resources in private subnets except ALB
- Security groups with minimal required access
- Bastion host for administrative access
- VPC Flow Logs enabled

### 2. Data Security  
- RDS encryption at rest enabled
- Redis encryption in transit enabled
- Secrets stored in Parameter Store with encryption
- Regular automated backups

### 3. Application Security
- HTTPS only (HTTP redirects to HTTPS)
- JWT token-based authentication
- Rate limiting on all API endpoints
- Input validation and sanitization

## Troubleshooting

### Common Deployment Issues

1. **ECS Service Won't Start**
   ```bash
   # Check task logs
   aws logs tail /ecs/accunode-api --follow
   
   # Check task definition
   aws ecs describe-task-definition --task-definition accunode-api-task
   ```

2. **Database Connection Issues**
   ```bash
   # Test from bastion
   telnet RDS-ENDPOINT 5432
   
   # Check security groups
   aws ec2 describe-security-groups --group-ids sg-rds-id
   ```

3. **Load Balancer Health Checks Failing**
   ```bash
   # Check target group health
   aws elbv2 describe-target-health --target-group-arn TARGET-GROUP-ARN
   
   # Test health endpoint directly
   curl -H "Host: api.accunode.com" http://CONTAINER-IP:8000/health
   ```

### Rollback Procedures

If deployment fails, follow the [Rollback Procedures](./rollback-procedures.md) guide to revert to the previous working version.

---

*For additional deployment troubleshooting, refer to the [Troubleshooting Guide](../troubleshooting/common-issues.md).*
