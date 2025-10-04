# 🏗️ AccuNode Complete Infrastructure Guide

## 📊 **Executive Summary**

**Project**: AccuNode - ML-based Default Rate Prediction API  
**Account**: AWS Account ID `461962182774`  
**Owner**: IAM User `pranit`  
**Environment**: Production (`prod`)  
**Daily Cost**: ~$3.60 USD (estimated monthly: ~$108 USD)

---

## 🎯 **Architecture Overview**

### **Core Application Stack**
```
Internet → ALB → ECS Fargate → RDS PostgreSQL
                    ↓
                ElastiCache Redis
                    ↓
              Parameter Store (Secrets)
```

### **CI/CD Pipeline**
```
GitHub (prod branch) → GitHub Actions → ECR → ECS Fargate → Production
```

---

## 🛠️ **Infrastructure Components**

### 1. **🖥️ Compute Layer - Amazon ECS Fargate**

**Purpose**: Run containerized FastAPI application without managing servers

**Configuration**:
- **Cluster**: `AccuNode-Production`
- **Platform**: AWS Fargate (Serverless containers)
- **Services**: 2 services running
  - `accunode-api-service` (Web API)
  - `accunode-worker-service` (Background tasks)

**Current Capacity**:
- **Normal**: 1 API + 1 Worker = 2 tasks
- **Maximum**: 2 API + 2 Worker = 4 tasks (auto-scaling)
- **Instance Size**: 0.25 vCPU, 512 MB RAM per task

**Why ECS Fargate?**
- ✅ No server management required
- ✅ Pay only for running containers
- ✅ Automatic scaling based on CPU
- ✅ Built-in load balancing
- ✅ Zero-downtime deployments

**Daily Cost**: ~$1.38 USD (ECS Fargate compute time)

---

### 2. **🌐 Load Balancing - Application Load Balancer (ALB)**

**Purpose**: Distribute incoming traffic across multiple API containers

**Configuration**:
- **Name**: `AccuNode-ECS-ALB`
- **DNS**: `AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com`
- **Scheme**: Internet-facing
- **Target Group**: `AccuNode-ECS-API-TG`
- **Health Check**: `/health` endpoint

**Why ALB?**
- ✅ High availability across zones
- ✅ SSL termination capability
- ✅ Health monitoring
- ✅ Integration with ECS auto-scaling

**Daily Cost**: ~$0.59 USD (ALB hourly charges + data processing)

---

### 3. **🗄️ Database Layer - Amazon RDS PostgreSQL**

**Purpose**: Primary database for application data

**Configuration**:
- **Instance**: `accunode-postgres`
- **Class**: `db.t3.small` (2 vCPU, 2 GB RAM)
- **Engine**: PostgreSQL 15.7
- **Storage**: 20 GB GP3 SSD
- **Backup**: 7 days retention
- **Multi-AZ**: No (cost optimization)

**Why RDS PostgreSQL?**
- ✅ Managed service (patching, backups)
- ✅ Automatic failover capability
- ✅ Point-in-time recovery
- ✅ Built-in monitoring

**Daily Cost**: ~$0.70 USD (instance + storage)

---

### 4. **⚡ Caching Layer - Amazon ElastiCache Redis**

**Purpose**: High-speed caching and session storage

**Configuration**:
- **Cluster**: `accunode-redis`
- **Node Type**: `cache.t3.micro` (2 vCPU, 0.5 GB)
- **Engine**: Redis
- **Nodes**: 1 (single-node setup)

**Why Redis?**
- ✅ Sub-millisecond response times
- ✅ Reduces database load
- ✅ Session management
- ✅ Rate limiting support

**Daily Cost**: ~$0.31 USD

---

### 5. **📦 Container Registry - Amazon ECR**

**Purpose**: Store and manage Docker container images

**Configuration**:
- **Repository**: `accunode`
- **URI**: `461962182774.dkr.ecr.us-east-1.amazonaws.com/accunode`
- **Image Scanning**: Enabled (security)
- **Encryption**: AES256
- **Lifecycle**: Keep 7 recent images

**Current Images**: 17 tagged images (~2-3 GB total)

**Why ECR?**
- ✅ Integrated with ECS
- ✅ Automatic vulnerability scanning
- ✅ Lifecycle management
- ✅ High availability

**Daily Cost**: ~$0.02 USD (storage charges)

---

### 6. **🔐 Secrets Management - AWS Systems Manager Parameter Store**

**Purpose**: Securely store sensitive configuration

**Configuration**:
- `/accunode/database-url` (SecureString)
- `/accunode/redis-url` (SecureString)  
- `/accunode/secret-key` (SecureString)

**Why Parameter Store?**
- ✅ Encryption at rest
- ✅ Fine-grained access control
- ✅ Audit logging
- ✅ Cost-effective for small volumes

**Daily Cost**: ~$0.00 USD (under free tier limits)

---

### 7. **🌐 Networking - Amazon VPC**

**Purpose**: Isolated network environment for resources

**Configuration**:
- **VPC**: `vpc-0cd7231cf6acb1d4f` (10.0.0.0/16)
- **Public Subnets**: 2 subnets across AZ (us-east-1a, us-east-1b)
- **Private Subnet**: 1 subnet (us-east-1a)
- **Internet Gateway**: Yes
- **NAT Gateway**: Yes (for private subnet egress)

**Security Groups**:
- `AccuNode-ECS-SG`: Controls container traffic
  - Port 8000: Internal API access (10.0.0.0/16)
  - Port 80/443: Internet access (0.0.0.0/0)

**Daily Cost**: ~$0.62 USD (NAT Gateway charges)

---

### 8. **📈 Auto Scaling - Application Auto Scaling**

**Purpose**: Automatically adjust capacity based on demand

**API Service Scaling**:
- **Min**: 1 instance
- **Max**: 2 instances
- **Trigger**: CPU > 70%
- **Scale Out**: 5 min cooldown
- **Scale In**: 5 min cooldown

**Worker Service Scaling**:
- **Min**: 1 instance
- **Max**: 2 instances
- **Trigger**: CPU > 60%
- **Scale Out**: 3 min cooldown
- **Scale In**: 5 min cooldown

**Why Auto Scaling?**
- ✅ Cost optimization during low usage
- ✅ Performance during high demand
- ✅ Automatic response to load changes

**Daily Cost**: ~$0.00 USD (no additional charges)

---

### 9. **🔍 Monitoring - Amazon CloudWatch**

**Purpose**: Monitor performance and trigger scaling

**Alarms Configured**:
- API Service CPU High/Low alarms
- Worker Service CPU High/Low alarms
- Auto-scaling trigger points

**Metrics Collected**:
- CPU utilization
- Memory utilization
- Network I/O
- Request count

**Daily Cost**: ~$0.00 USD (under free tier)

---

## 🚀 **CI/CD Pipeline Detailed**

### **GitHub Actions Workflow** (`.github/workflows/ci-cd.yml`)

**Triggers**:
- **Pull Request** to `prod`: Security scan + build test (no deployment)
- **Push** to `prod`: Full deployment pipeline

**Pipeline Stages**:

#### 1. **Security & Code Quality** (PR only)
```yaml
- Checkout code
- Install Python dependencies
- Run Bandit security scanner
- Check for known vulnerabilities
- Upload security reports
```

#### 2. **Build & Test**
```yaml
- Build Docker image (linux/amd64)
- Tag with commit SHA: prod-<sha>
- Push to ECR with multiple tags
- Clean up old/problematic images
```

#### 3. **Production Deployment** (Push to prod only)
```yaml
- Verify image exists in ECR
- Update task definitions with new image
- Register new task definitions  
- Deploy API service
- Deploy Worker service
- Wait for deployment completion
- Verify health status
```

#### 4. **Rollback** (On failure)
```yaml
- Get previous task definition versions
- Rollback API service
- Rollback Worker service
- Notify of rollback completion
```

**Image Tagging Strategy**:
- `prod-<commit-sha>`: Unique deployment tag
- `latest`: Latest production version
- `prod`: Branch-based tag

---

## 💰 **Cost Breakdown & Optimization**

### **Daily Cost Analysis** (Based on actual usage data)

| Service | Daily Cost | Monthly Estimate | Purpose |
|---------|------------|------------------|---------|
| **ECS Fargate** | $1.38 | $41.40 | Container compute time |
| **RDS PostgreSQL** | $0.70 | $21.00 | Database instance + storage |
| **ALB** | $0.59 | $17.70 | Load balancing |
| **VPC (NAT Gateway)** | $0.62 | $18.60 | Network egress |
| **ElastiCache Redis** | $0.31 | $9.30 | Caching layer |
| **ECR** | $0.02 | $0.60 | Container image storage |
| **Parameter Store** | $0.00 | $0.00 | Secrets management |
| **CloudWatch** | $0.00 | $0.00 | Monitoring |
| **Total** | **$3.62** | **$108.60** | |

### **Cost Optimization Opportunities**:

1. **RDS**: Switch to `db.t3.micro` → Save ~$10/month
2. **NAT Gateway**: Use NAT Instance → Save ~$15/month  
3. **ECS**: Spot instances for worker → Save ~$8/month
4. **ElastiCache**: Use `cache.t3.nano` → Save ~$4/month

**Potential Monthly Savings**: ~$37 USD (Reduced to ~$71/month)

---

## 👥 **Team Member Onboarding Guide**

### **Prerequisites for New Team Members**

#### 1. **Required Accounts & Access**
- GitHub account with repo access
- AWS Console access (IAM user)
- AWS CLI configured locally

#### 2. **Local Development Setup**
```bash
# Clone repository
git clone https://github.com/betterresumes/default-rate-backend.git
cd default-rate-backend

# Install dependencies
pip install -r requirements.dev.txt

# Set up environment
cp .env.example .env
# Edit .env with development database URLs

# Run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 3. **AWS CLI Configuration**
```bash
# Configure AWS CLI
aws configure
# Enter: Access Key, Secret Key, Region (us-east-1), Output (json)

# Verify access
aws sts get-caller-identity
aws ecs list-clusters
```

### **Common Operations for Team Members**

#### **Deploy to Production**
```bash
# Method 1: Git push (Recommended)
git checkout prod
git merge feature-branch
git push origin prod
# → Automatically triggers CI/CD pipeline

# Method 2: Manual deployment (Emergency only)
aws ecs update-service --cluster AccuNode-Production \
  --service accunode-api-service --force-new-deployment
```

#### **View Logs**
```bash
# ECS service logs
aws logs tail /ecs/accunode-api --follow

# Recent deployment events
aws ecs describe-services --cluster AccuNode-Production \
  --services accunode-api-service \
  --query 'services[0].events[0:5]'
```

#### **Scale Services Manually**
```bash
# Scale API service
aws ecs update-service --cluster AccuNode-Production \
  --service accunode-api-service --desired-count 2

# Scale worker service  
aws ecs update-service --cluster AccuNode-Production \
  --service accunode-worker-service --desired-count 2
```

#### **Database Operations**
```bash
# Connect to RDS (requires VPN or bastion)
psql -h accunode-postgres.xxxxx.us-east-1.rds.amazonaws.com \
  -U admin -d accunode_production

# Create database backup
aws rds create-db-snapshot \
  --db-instance-identifier accunode-postgres \
  --db-snapshot-identifier manual-backup-$(date +%Y%m%d)
```

#### **Monitor Costs**
```bash
# View recent costs
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-05 \
  --granularity DAILY --metrics BlendedCost

# Set up cost alerts (one-time setup)
aws budgets create-budget --account-id 461962182774 \
  --budget file://cost-budget.json
```

### **Emergency Procedures**

#### **Rollback Deployment**
```bash
# Get previous task definition
PREV_TASK_ARN=$(aws ecs describe-services \
  --cluster AccuNode-Production --services accunode-api-service \
  --query 'services[0].deployments[1].taskDefinition' --output text)

# Rollback
aws ecs update-service --cluster AccuNode-Production \
  --service accunode-api-service --task-definition $PREV_TASK_ARN
```

#### **Stop All Services** (Emergency shutdown)
```bash
# Scale down to 0
aws ecs update-service --cluster AccuNode-Production \
  --service accunode-api-service --desired-count 0

aws ecs update-service --cluster AccuNode-Production \
  --service accunode-worker-service --desired-count 0
```

#### **Health Checks**
```bash
# Check service status
aws ecs describe-services --cluster AccuNode-Production \
  --services accunode-api-service accunode-worker-service

# Test API endpoint
curl -f https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/health

# Check database connectivity
aws rds describe-db-instances --db-instance-identifier accunode-postgres
```

---

## 🔒 **Security & Compliance**

### **Security Features Implemented**

1. **Network Security**:
   - VPC isolation
   - Security groups with minimal required access
   - Private subnets for database
   - ALB with SSL/TLS support

2. **Container Security**:
   - ECR vulnerability scanning
   - Non-root container user
   - Security headers middleware
   - Rate limiting protection

3. **Secrets Management**:
   - Parameter Store with encryption
   - No secrets in code/environment files
   - IAM role-based access

4. **Database Security**:
   - Encrypted at rest
   - VPC-only access
   - Automated backups
   - Point-in-time recovery

### **Compliance Considerations**
- All data encrypted at rest and in transit
- Audit logs via CloudTrail (if enabled)
- Role-based access control
- Regular security scanning

---

## 🚨 **Monitoring & Alerting**

### **Current Monitoring**
- **CloudWatch Metrics**: CPU, memory, network for all services
- **Auto-scaling Alarms**: CPU-based scaling triggers
- **Health Checks**: ALB health monitoring
- **Application Logs**: Structured logging to CloudWatch

### **Recommended Additional Monitoring**
```bash
# Set up additional alarms (run once)
aws cloudwatch put-metric-alarm \
  --alarm-name "High-Error-Rate" \
  --alarm-description "API error rate > 5%" \
  --metric-name "4XXError" \
  --namespace "AWS/ApplicationELB" \
  --statistic "Sum" \
  --period 300 \
  --threshold 5 \
  --comparison-operator "GreaterThanThreshold"
```

### **Log Analysis**
```bash
# Search application logs
aws logs filter-log-events \
  --log-group-name "/ecs/accunode-api" \
  --filter-pattern "ERROR"

# Export logs for analysis
aws logs create-export-task \
  --log-group-name "/ecs/accunode-api" \
  --from $(date -d "1 day ago" +%s)000 \
  --to $(date +%s)000 \
  --destination "s3://your-log-bucket"
```

---

## 📚 **Troubleshooting Guide**

### **Common Issues & Solutions**

#### **1. Deployment Failing**
```bash
# Check deployment status
aws ecs describe-services --cluster AccuNode-Production \
  --services accunode-api-service

# Check task logs
aws logs tail /ecs/accunode-api --since 1h

# Common fixes:
# - Verify ECR image exists
# - Check Parameter Store secrets
# - Verify task definition syntax
```

#### **2. High CPU/Memory Usage**
```bash
# Check current metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS --metric-name CPUUtilization \
  --start-time $(date -d "1 hour ago" -u +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 --statistics Average

# Solutions:
# - Manual scaling if needed
# - Check for inefficient queries
# - Review auto-scaling thresholds
```

#### **3. Database Connection Issues**
```bash
# Test RDS connectivity
aws rds describe-db-instances --db-instance-identifier accunode-postgres

# Check security groups
aws ec2 describe-security-groups --group-ids sg-0904e16e00d5e08c7

# Verify Parameter Store values
aws ssm get-parameter --name "/accunode/database-url" --with-decryption
```

#### **4. Load Balancer Issues**
```bash
# Check ALB status
aws elbv2 describe-load-balancers

# Check target health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:461962182774:targetgroup/AccuNode-ECS-API-TG/07039abc0aad166f
```

---

## 🎯 **Performance Optimization**

### **Current Performance Settings**
- **ECS Tasks**: 0.25 vCPU, 512 MB RAM
- **Auto-scaling**: CPU-based (70% API, 60% Worker)
- **Database**: db.t3.small, GP3 storage
- **Caching**: Redis for frequently accessed data

### **Optimization Recommendations**

#### **1. Application Level**
```python
# Connection pooling (already implemented)
DATABASE_POOL_SIZE = 10
DATABASE_MAX_OVERFLOW = 20

# Redis caching strategy
CACHE_TTL = 3600  # 1 hour for predictions
CACHE_PREDICTION_RESULTS = True
```

#### **2. Database Optimization**
```sql
-- Index optimization
CREATE INDEX CONCURRENTLY idx_predictions_created_at ON predictions(created_at);
CREATE INDEX CONCURRENTLY idx_organizations_tenant_id ON organizations(tenant_id);

-- Query optimization
EXPLAIN ANALYZE SELECT * FROM predictions WHERE tenant_id = ?;
```

#### **3. Container Optimization**
```dockerfile
# Multi-stage build (already implemented)
# Minimal base image
# Non-root user
# Health checks
```

---

## 🔄 **Backup & Disaster Recovery**

### **Current Backup Strategy**

#### **Database Backups**
- **Automated**: 7-day retention
- **Manual snapshots**: As needed
- **Point-in-time recovery**: Up to 7 days

#### **Application Backups**
- **Container images**: Stored in ECR
- **Configuration**: Infrastructure as Code in Git
- **Secrets**: Parameter Store (encrypted)

### **Disaster Recovery Plan**

#### **RTO/RPO Targets**
- **RTO** (Recovery Time Objective): 15 minutes
- **RPO** (Recovery Point Objective): 1 hour

#### **Recovery Procedures**
```bash
# 1. Restore database from snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier accunode-postgres-restored \
  --db-snapshot-identifier manual-backup-20251004

# 2. Update Parameter Store with new DB endpoint
aws ssm put-parameter --name "/accunode/database-url" \
  --value "postgresql://user:pass@new-endpoint:5432/db" \
  --type SecureString --overwrite

# 3. Force deployment with latest image
aws ecs update-service --cluster AccuNode-Production \
  --service accunode-api-service --force-new-deployment
```
