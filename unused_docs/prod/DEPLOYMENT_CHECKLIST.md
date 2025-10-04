# 📋 **AccuNode AWS Deployment Checklist**

## **Pre-Deployment Requirements**
- [ ] AWS Account with billing setup
- [ ] Domain name registered (optional but recommended)
- [ ] GitHub repository: https://github.com/accunodeai/server
- [ ] Local environment with AWS CLI, Docker installed
- [ ] Access to current database for migration

---

## **Phase 1: Core Infrastructure (Day 1-2)**
- [ ] AWS CLI configured with IAM user
- [ ] VPC created with public/private subnets
- [ ] Security groups configured
- [ ] NAT Gateway deployed
- [ ] RDS PostgreSQL created (⏰ 5-10 minutes)
- [ ] ElastiCache Redis created (⏰ 3-5 minutes)
- [ ] S3 bucket created and ML models uploaded
- [ ] Secrets stored in Parameter Store

## **Phase 2: Container & Application (Day 3)**
- [ ] ECR repository created
- [ ] IAM roles for ECS created
- [ ] Code updated for AWS S3 integration
- [ ] Docker image built and pushed
- [ ] ECS cluster created
- [ ] Task definition registered

## **Phase 3: Load Balancing (Day 3-4)**
- [ ] Target group created
- [ ] Application Load Balancer created
- [ ] ECS service deployed and running
- [ ] Health checks passing
- [ ] SSL certificate requested (⏰ Manual DNS validation required)
- [ ] HTTPS listener configured

## **Phase 4: Scaling & Monitoring (Day 4)**
- [ ] Auto-scaling policies configured
- [ ] CloudWatch alarms created
- [ ] SNS notifications set up

## **Phase 5: Data & CI/CD (Day 5)**
- [ ] Database migration completed
- [ ] GitHub Actions workflow configured
- [ ] Final testing completed
- [ ] Domain DNS pointing to ALB (optional)

---

## **Critical Wait Times**
| Service | Wait Time | Can Continue? |
|---------|-----------|---------------|
| RDS PostgreSQL | 5-10 minutes | ❌ Need for secrets |
| ElastiCache Redis | 3-5 minutes | ❌ Need for secrets |
| NAT Gateway | 2-3 minutes | ✅ Can continue |
| ECS Service Deploy | 3-5 minutes | ❌ Need for testing |
| SSL Certificate | Manual DNS validation | ✅ Can use HTTP first |

---

## **Important Variables to Save**
```bash
# Save these values during deployment:
export VPC_ID="vpc-xxxxx"
export PUBLIC_SUBNET_1="subnet-xxxxx"  
export PUBLIC_SUBNET_2="subnet-xxxxx"
export PRIVATE_SUBNET_1="subnet-xxxxx"
export PRIVATE_SUBNET_2="subnet-xxxxx"
export ALB_SG_ID="sg-xxxxx"
export ECS_SG_ID="sg-xxxxx"
export RDS_SG_ID="sg-xxxxx"
export REDIS_SG_ID="sg-xxxxx"
export DB_PASSWORD="xxxxx"
export BUCKET_NAME="default-rate-ml-models-prod-xxxxx"
export ECR_URI="xxxxx.dkr.ecr.us-east-1.amazonaws.com/default-rate-app"
export ALB_DNS="xxxxx.us-east-1.elb.amazonaws.com"
export TARGET_GROUP_ARN="arn:aws:elasticloadbalancing:us-east-1:xxxxx:targetgroup/xxxxx"
export ALB_ARN="arn:aws:elasticloadbalancing:us-east-1:xxxxx:loadbalancer/app/xxxxx"
```

---

## **Quick Commands Reference**

### **Check Service Status**
```bash
# ECS Service
aws ecs describe-services --cluster default-rate-cluster --services default-rate-service

# RDS Status
aws rds describe-db-instances --db-instance-identifier default-rate-db

# Redis Status  
aws elasticache describe-cache-clusters --cache-cluster-id default-rate-redis

# ALB Health
aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN
```

### **View Logs**
```bash
# ECS Logs
aws logs tail /ecs/default-rate --follow

# Recent errors
aws logs filter-events --log-group-name /ecs/default-rate --filter-pattern "ERROR"
```

### **Scale Service**
```bash
# Scale up
aws ecs update-service --cluster default-rate-cluster --service default-rate-service --desired-count 3

# Scale down
aws ecs update-service --cluster default-rate-cluster --service default-rate-service --desired-count 1
```

---

## **Cost Monitoring Commands**
```bash
# Current month costs
aws ce get-cost-and-usage \
  --time-period Start=2025-10-01,End=2025-10-31 \
  --granularity MONTHLY \
  --metrics BlendedCost

# Set up billing alerts (run once)
aws budgets create-budget --account-id $(aws sts get-caller-identity --query Account --output text) --budget '{
  "BudgetName": "DefaultRateMonthlyBudget",
  "BudgetLimit": {
    "Amount": "150",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}'
```

---

## **Emergency Rollback**
```bash
# If deployment fails, rollback to previous task definition
aws ecs update-service \
  --cluster default-rate-cluster \
  --service default-rate-service \
  --task-definition default-rate-task:PREVIOUS_REVISION

# Stop service (emergency)
aws ecs update-service \
  --cluster default-rate-cluster \
  --service default-rate-service \
  --desired-count 0
```

---

## **Success Criteria**
- [ ] Health endpoint responds: `curl https://yourdomain.com/health`
- [ ] API docs accessible: `https://yourdomain.com/docs`
- [ ] Database connection working
- [ ] Redis connection working  
- [ ] ML models loading from S3
- [ ] Auto-scaling policies active
- [ ] CloudWatch alarms configured
- [ ] SSL certificate validated
- [ ] CI/CD pipeline working

**Total Deployment Time: 4-5 days (including wait times and testing)**
