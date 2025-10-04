# 🚀 AccuNode Team Onboarding & Access Guide

## 👥 **Welcome to the AccuNode Team!**

This guide will help new team members get full access to our AWS infrastructure and understand how everything works together.

---

## 📋 **Table of Contents**

1. [🎯 Project Overview](#-project-overview)
2. [🔐 Getting Access](#-getting-access)
3. [🛠️ Setup Your Environment](#️-setup-your-environment)
4. [🏗️ Understanding Our Infrastructure](#️-understanding-our-infrastructure)
5. [🚀 Daily Operations](#-daily-operations)
6. [🗄️ Database Access](#️-database-access)
7. [📊 Monitoring & Costs](#-monitoring--costs)
8. [🆘 Emergency Procedures](#-emergency-procedures)
9. [📚 Additional Resources](#-additional-resources)

---

## 🎯 **Project Overview**

**AccuNode** is a machine learning-based default rate prediction API built with FastAPI and deployed on AWS.

### **Key Information**
- **AWS Account**: `461962182774`
- **Project Owner**: Pranit (pranit@company.com)
- **GitHub Repo**: `betterresumes/default-rate-backend`
- **Production Branch**: `prod` (not main!)
- **Environment**: Production only
- **Monthly Cost**: ~$108 USD

### **What We Built**
- 🤖 **ML API**: Predict default rates using trained models
- 🔄 **Auto-Scaling**: Automatically handles traffic spikes
- 🛡️ **Secure**: Multi-tenant authentication system
- 📊 **Monitored**: Complete observability and alerting
- 🚀 **CI/CD**: Automated deployments from GitHub

---

## 🔐 **Getting Access**

### **1. GitHub Repository Access**
Ask the project owner to add you to the `betterresumes/default-rate-backend` repository with **Developer** or **Maintainer** permissions.

### **2. AWS Console Access**
You'll need an AWS IAM user account. Ask the admin to create one for you:

**Required Permissions:**
- ECS Full Access (view services, logs)
- RDS Read Access (view database status)
- CloudWatch Read Access (view metrics, logs)
- ECR Read Access (view container images)
- Systems Manager Read Access (view parameters, not secrets)

**AWS Console Login URL:**
```
https://461962182774.signin.aws.amazon.com/console
```

### **3. Database Access** 
Database access is provided through a **Bastion EC2 instance** for security. You'll need:
- EC2 SSH key pair
- Instructions to connect through bastion

---

## 🛠️ **Setup Your Environment**

### **1. Install Required Tools**
```bash
# AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip && sudo ./aws/install

# Docker (for local development)
# Follow Docker installation guide for your OS

# Git (if not already installed)
# Python 3.11+ (for local development)
```

### **2. Configure AWS CLI**
```bash
# Configure with your AWS credentials
aws configure
```
**Enter when prompted:**
- Access Key ID: [Your AWS access key]
- Secret Access Key: [Your AWS secret key] 
- Default region: `us-east-1`
- Default output: `json`

### **3. Verify Access**
```bash
# Test AWS connection
aws sts get-caller-identity

# Should show your user info and account 461962182774
```

### **4. Clone Repository**
```bash
git clone https://github.com/betterresumes/default-rate-backend.git
cd default-rate-backend

# Important: Switch to prod branch (not main!)
git checkout prod
```

### **5. Local Development Setup**
```bash
# Install Python dependencies
pip install -r requirements.dev.txt

# Copy environment template
cp .env.example .env

# Edit .env with development database connection
# (You'll get these details from the admin)
```

---

## 🏗️ **Understanding Our Infrastructure**

### **Architecture Overview**
```
Internet Users
    ↓
Application Load Balancer (ALB)
    ↓
ECS Fargate Services (Auto-scaling 1-4 containers)
    ├── API Service (FastAPI app)
    └── Worker Service (Background tasks)
    ↓
RDS PostgreSQL Database ← → ElastiCache Redis
    ↑
Bastion EC2 (for secure database access)
```

### **Key AWS Services We Use**

#### **🖥️ ECS Fargate (Compute)**
- **Cluster**: `AccuNode-Production`
- **Services**: API + Worker services
- **Auto-scaling**: Based on CPU usage
- **Platform**: Serverless containers

#### **🗄️ RDS PostgreSQL (Database)**
- **Instance**: `accunode-postgres`
- **Size**: `db.t3.small`
- **Storage**: 20GB GP3 SSD
- **Backups**: 7 days retention

#### **⚡ ElastiCache Redis (Cache)**
- **Instance**: `accunode-redis` 
- **Size**: `cache.t3.micro`
- **Purpose**: Session storage, rate limiting

#### **📦 ECR (Container Registry)**
- **Repository**: `accunode`
- **Images**: Stores our Docker containers
- **Lifecycle**: Keeps 7 recent versions

#### **🔐 Parameter Store (Secrets)**
- Database connection strings
- API keys and secrets
- Application configuration

#### **🌐 VPC Networking**
- Custom VPC with public/private subnets
- Security groups for access control
- NAT Gateway for private subnet internet access

---

## 🚀 **Daily Operations**

### **View Service Status**
```bash
# Check all services
aws ecs describe-services \
  --cluster AccuNode-Production \
  --services accunode-api-service accunode-worker-service

# Quick status check
aws ecs list-services --cluster AccuNode-Production
```

### **View Application Logs**
```bash
# Live API logs
aws logs tail /ecs/accunode-api --follow

# Recent logs (last hour)
aws logs tail /ecs/accunode-api --since 1h

# Worker service logs
aws logs tail /ecs/accunode-worker --follow
```

### **Deploy New Version**
**Method 1: Automatic (Recommended)**
```bash
# Make your changes, commit, and push to prod branch
git add .
git commit -m "feat: your feature description"
git push origin prod

# This automatically triggers CI/CD pipeline
```

**Method 2: Manual (Emergency only)**
```bash
# Force new deployment with current image
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-api-service \
  --force-new-deployment
```

### **Scale Services**
```bash
# Scale API to 2 instances
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-api-service \
  --desired-count 2

# Scale Worker to 2 instances
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-worker-service \
  --desired-count 2

# Auto-scaling will still work within limits
```

### **Check Container Images**
```bash
# List recent images
aws ecr list-images --repository-name accunode

# Get image details
aws ecr describe-images --repository-name accunode
```

---

## 🗄️ **Database Access**

### **Architecture**
For security, our RDS database is in a private subnet. Access is provided through a **Bastion EC2 instance**.

```
Your Computer → Bastion EC2 → RDS PostgreSQL
```

### **Connect to Database**

#### **Step 1: Connect to Bastion**
```bash
# Get the bastion instance details
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=AccuNode-Bastion" \
  --query 'Reservations[0].Instances[0].[InstanceId,PublicIpAddress,State.Name]'

# SSH to bastion (you'll need the .pem key file)
ssh -i bastion-access-key.pem ec2-user@<BASTION_PUBLIC_IP>
```

#### **Step 2: Connect to Database from Bastion**
```bash
# From bastion instance, connect to RDS
psql -h accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com \
     -U admin \
     -d accunode_production \
     -p 5432

# You'll be prompted for the database password
```

#### **Step 3: Useful Database Commands**
```sql
-- List all tables
\dt

-- Check database size
SELECT pg_size_pretty(pg_database_size('accunode_production'));

-- View recent predictions
SELECT * FROM predictions ORDER BY created_at DESC LIMIT 10;

-- Check active connections
SELECT count(*) FROM pg_stat_activity;

-- Exit database
\q
```

### **Alternative: Port Forwarding**
```bash
# Create SSH tunnel to access DB from your local machine
ssh -i bastion-access-key.pem -L 5432:accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com:5432 ec2-user@<BASTION_IP>

# Now connect locally
psql -h localhost -U admin -d accunode_production -p 5432
```

### **Database Backups**
```bash
# Create manual backup
aws rds create-db-snapshot \
  --db-instance-identifier accunode-postgres \
  --db-snapshot-identifier manual-backup-$(date +%Y%m%d)

# List backups
aws rds describe-db-snapshots \
  --db-instance-identifier accunode-postgres
```

---

## 📊 **Monitoring & Costs**

### **CloudWatch Metrics**
```bash
# View ECS service metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=accunode-api-service Name=ClusterName,Value=AccuNode-Production \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average

# View database metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name CPUUtilization \
  --dimensions Name=DBInstanceIdentifier,Value=accunode-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average
```

### **Cost Monitoring**
```bash
# Daily costs for last 7 days
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '7 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost

# Cost by service
aws ce get-cost-and-usage \
  --time-period Start=$(date -d '30 days ago' +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=DIMENSION,Key=SERVICE
```

### **Health Checks**
```bash
# Check ALB health
curl -f https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/health

# Check service health via ECS
aws ecs describe-services \
  --cluster AccuNode-Production \
  --services accunode-api-service \
  --query 'services[0].[serviceName,runningCount,desiredCount,status]'
```

---

## 🆘 **Emergency Procedures**

### **Rollback Deployment**
```bash
# Get previous task definition
PREV_TASK=$(aws ecs describe-services \
  --cluster AccuNode-Production \
  --services accunode-api-service \
  --query 'services[0].deployments[1].taskDefinition' \
  --output text)

# Rollback API service
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-api-service \
  --task-definition $PREV_TASK

# Rollback Worker service  
PREV_WORKER=$(aws ecs describe-services \
  --cluster AccuNode-Production \
  --services accunode-worker-service \
  --query 'services[0].deployments[1].taskDefinition' \
  --output text)

aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-worker-service \
  --task-definition $PREV_WORKER
```

### **Scale Down (Emergency Stop)**
```bash
# Scale all services to 0 (emergency shutdown)
aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-api-service \
  --desired-count 0

aws ecs update-service \
  --cluster AccuNode-Production \
  --service accunode-worker-service \
  --desired-count 0
```

### **Check Service Events**
```bash
# Check recent service events for issues
aws ecs describe-services \
  --cluster AccuNode-Production \
  --services accunode-api-service \
  --query 'services[0].events[0:10]'
```

### **Database Issues**
```bash
# Check RDS status
aws rds describe-db-instances \
  --db-instance-identifier accunode-postgres

# Check recent RDS events
aws rds describe-events \
  --source-identifier accunode-postgres \
  --source-type db-instance \
  --max-records 10
```

---

## 📚 **Additional Resources**

### **AWS Console Quick Links**
- [ECS Cluster](https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/AccuNode-Production)
- [RDS Database](https://console.aws.amazon.com/rds/home?region=us-east-1#database:id=accunode-postgres)
- [CloudWatch Logs](https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#logsV2:log-groups)
- [Cost Dashboard](https://console.aws.amazon.com/billing/home#/)
- [Parameter Store](https://console.aws.amazon.com/systems-manager/parameters/?region=us-east-1)

### **GitHub Links**
- [Repository](https://github.com/betterresumes/default-rate-backend)
- [GitHub Actions](https://github.com/betterresumes/default-rate-backend/actions)
- [Issues](https://github.com/betterresumes/default-rate-backend/issues)

### **Documentation Structure**
```
docs/
├── team/
│   ├── TEAM_ONBOARDING_GUIDE.md (this file)
│   └── QUICK_REFERENCE.md
├── aws/
│   ├── infrastructure/
│   │   ├── COMPLETE_INFRASTRUCTURE_GUIDE.md
│   │   └── COST_OPTIMIZATION_GUIDE.md
│   ├── deployment/
│   │   ├── CI_CD_SETUP.md
│   │   └── ROLLBACK_PLAN.md
│   ├── database/
│   │   ├── RDS_ACCESS_SETUP.md
│   │   └── EC2_BASTION_SETUP.md
│   └── security/
│       └── SECURITY_AUDIT.md
```

### **Troubleshooting Checklist**
1. ✅ Check service status in AWS Console
2. ✅ Review application logs via CloudWatch
3. ✅ Verify GitHub Actions pipeline status
4. ✅ Check auto-scaling events
5. ✅ Validate network connectivity
6. ✅ Review recent deployments
7. ✅ Contact team lead if issue persists

### **Best Practices**
- 🔐 **Never commit secrets** to Git
- 🚀 **Always test in PR first** before pushing to prod
- 📊 **Monitor costs regularly** 
- 🔄 **Use auto-scaling** instead of manual scaling
- 📝 **Document any infrastructure changes**
- 🛡️ **Follow security guidelines** for database access

---

## 🎯 **Next Steps for New Team Members**

### **Week 1: Getting Started**
- [ ] Get AWS console access
- [ ] Set up local development environment
- [ ] Clone repository and checkout `prod` branch
- [ ] Run application locally with dev database
- [ ] Review codebase and documentation

### **Week 2: Understanding Infrastructure**
- [ ] Connect to bastion and database
- [ ] Practice common AWS CLI commands
- [ ] Monitor services and logs
- [ ] Test CI/CD with a small PR
- [ ] Review cost dashboard

### **Week 3: Contributing**
- [ ] Make your first feature contribution
- [ ] Deploy to production via GitHub
- [ ] Monitor your deployment
- [ ] Help improve documentation
- [ ] Share feedback on onboarding process

---

## 📞 **Getting Help**

### **Technical Issues**
1. Check this documentation first
2. Search GitHub Issues
3. Ask in team Slack channel
4. Contact infrastructure owner: Pranit

### **AWS Access Issues**  
1. Verify your AWS credentials
2. Check IAM permissions with admin
3. Ensure you're in correct AWS region (us-east-1)

### **Emergency Contact**
- **Infrastructure Owner**: Pranit (pranit@company.com)
- **AWS Account ID**: 461962182774
- **Escalation**: Create GitHub issue with `urgent` label

---

*Team Onboarding Guide v1.0 | Updated: Oct 4, 2025 | Owner: Pranit*

**Welcome to the team! 🚀 You've got this!**
