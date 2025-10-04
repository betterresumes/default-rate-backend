# 🚀 **AccuNode Final Production Architecture**

## **📋 Project Overview**
- **Project**: AccuNode (Financial Risk Assessment Platform)
- **Architecture**: Simple, scalable, cost-effective
- **Target**: 500-2000+ concurrent users
- **Cost Range**: $109-250/month
- **Complexity**: Low (no over-engineering)

---

# **🏗️ Final System Architecture**

```
                    Internet Users
                          ↓
    ┌─────────────────────────────────────────────────────┐
    │            AWS APPLICATION LOAD BALANCER            │
    │          Health Checks + Traffic Distribution       │
    │                  ($18/month)                        │
    └─────────────────────┬───────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │                 API SERVER TIER                     │
    │          (Auto-Scaling: 2-4 servers)               │
    │                                                     │
    │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
    │ │API Server 1 │ │API Server 2 │ │API Server 3*│   │
    │ │ t3.small    │ │ t3.small    │ │ t3.small    │   │
    │ │ $15/month   │ │ $15/month   │ │ $15/month   │   │
    │ │             │ │             │ │             │   │
    │ │FastAPI Only │ │FastAPI Only │ │FastAPI Only │   │
    │ │4 Uvicorn    │ │4 Uvicorn    │ │4 Uvicorn    │   │
    │ │Workers      │ │Workers      │ │Workers      │   │
    │ └─────────────┘ └─────────────┘ └─────────────┘   │
    └─────────────────────┬───────────────────────────────┘
                          │ *Auto-scales based on traffic
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │                REDIS TASK QUEUE                     │
    │               (Session Cache)                       │
    │              t3.micro → t3.small                   │
    │              ($15-30/month)                        │
    └─────────────────────┬───────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │               WORKER SERVER TIER                    │
    │          (Auto-Scaling: 2-6 servers)               │
    │                                                     │
    │ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
    │ │Worker Node 1│ │Worker Node 2│ │Worker Node N│   │
    │ │ t3.small    │ │ t3.small    │ │ t3.small    │   │
    │ │ $15/month   │ │ $15/month   │ │ $15/month   │   │
    │ │             │ │             │ │             │   │
    │ │4 Celery     │ │4 Celery     │ │4 Celery     │   │
    │ │Workers      │ │Workers      │ │Workers      │   │
    │ │ML Processing│ │ML Processing│ │ML Processing│   │
    │ └─────────────┘ └─────────────┘ └─────────────┘   │
    └─────────────────────┬───────────────────────────────┘
                          │
                          ▼
    ┌─────────────────────────────────────────────────────┐
    │              SINGLE DATABASE                        │
    │            RDS PostgreSQL                          │
    │       t3.micro → t3.small → t3.medium              │
    │           ($16-65/month)                           │
    │                                                    │
    │  ┌─────────────────────────────────────────────┐   │
    │  │          S3 BUCKET                          │   │
    │  │      ML Models Storage                      │   │
    │  │        ($1-3/month)                        │   │
    │  └─────────────────────────────────────────────┘   │
    └─────────────────────────────────────────────────────┘
```

---

# **💰 Cost Scaling Matrix**

## **Phase 1: Startup ($109/month)**
```bash
Traffic:           500-800 concurrent users
API Servers:       2x t3.small          ($30/month)
Worker Servers:    2x t3.small          ($30/month)  
Redis:            1x t3.micro           ($15/month)
Database:         1x RDS t3.micro       ($16/month)
Load Balancer:    1x ALB                ($18/month)
─────────────────────────────────────────────────────
TOTAL:                                  $109/month

Performance:
- API Response: <200ms
- Background Tasks: 8 parallel workers  
- ML Predictions: ~300 companies/hour
```

## **Phase 2: Growth ($154/month)**
```bash
Traffic:           800-1200 concurrent users
API Servers:       3x t3.small          ($45/month)  ← Add 1 API server
Worker Servers:    4x t3.small          ($60/month)  ← Add 2 workers
Redis:            1x t3.small           ($30/month)  ← Upgrade Redis
Database:         1x RDS t3.micro       ($16/month)
Load Balancer:    1x ALB                ($18/month)
─────────────────────────────────────────────────────
TOTAL:                                  $169/month

Performance:
- API Response: <150ms
- Background Tasks: 16 parallel workers
- ML Predictions: ~600 companies/hour
```

## **Phase 3: Scale ($229/month)**
```bash
Traffic:           1200-2000+ concurrent users
API Servers:       4x t3.small          ($60/month)  ← Add 1 more API
Worker Servers:    6x t3.small          ($90/month)  ← Add 2 more workers
Redis:            1x t3.small           ($30/month)
Database:         1x RDS t3.small       ($32/month)  ← Upgrade DB
Load Balancer:    1x ALB                ($18/month)
─────────────────────────────────────────────────────
TOTAL:                                  $230/month

Performance:
- API Response: <100ms
- Background Tasks: 24 parallel workers
- ML Predictions: ~900 companies/hour
```

---

# **⚙️ Auto-Scaling Configuration**

## **API Server Auto-Scaling**
```bash
# Scaling Triggers:
SCALE_UP_TRIGGERS:
  - ALB target response time > 300ms for 3 minutes
  - API server CPU > 70% for 5 minutes  
  - API server memory > 80% for 3 minutes
  
SCALE_DOWN_TRIGGERS:
  - ALB target response time < 100ms for 10 minutes
  - API server CPU < 30% for 15 minutes
  - API server memory < 50% for 15 minutes

# Scaling Limits:
MIN_API_SERVERS: 2        # Always maintain 2 for redundancy
MAX_API_SERVERS: 4        # Maximum 4 servers for cost control
COOLDOWN_PERIOD: 300      # 5 minutes between scaling actions
```

## **Worker Server Auto-Scaling**  
```bash
# Scaling Triggers:
SCALE_UP_TRIGGERS:
  - Redis queue length > 20 tasks for 3 minutes
  - Worker CPU > 80% for 5 minutes
  - Average task wait time > 60 seconds
  
SCALE_DOWN_TRIGGERS:
  - Redis queue length < 5 tasks for 10 minutes  
  - Worker CPU < 30% for 15 minutes
  - No tasks in queue for 20 minutes

# Scaling Limits:
MIN_WORKER_SERVERS: 2     # Always maintain 2 for processing
MAX_WORKER_SERVERS: 6     # Maximum 6 servers for cost control
COOLDOWN_PERIOD: 300      # 5 minutes between scaling actions
```

---

# **🔧 Component Specifications**

## **API Servers**
```yaml
Instance_Type: t3.small
vCPU: 2
RAM: 2GB
Storage: 8GB EBS GP2
OS: Amazon Linux 2

Application:
  - FastAPI with 4 Uvicorn workers
  - JWT authentication
  - Rate limiting: 100 req/min per user
  - Health endpoint: /health
  - Metrics endpoint: /metrics

Container:
  - Docker image: accunode:api-latest
  - Port: 8000
  - Environment: Production
  - Restart: always

Load_Balancer_Config:
  - Health check: GET /health
  - Interval: 30 seconds
  - Timeout: 10 seconds
  - Healthy threshold: 2
  - Unhealthy threshold: 3
```

## **Worker Servers**
```yaml
Instance_Type: t3.small  
vCPU: 2
RAM: 2GB
Storage: 8GB EBS GP2
OS: Amazon Linux 2

Application:
  - Celery with 4 worker processes
  - ML model processing
  - Bulk data upload processing
  - Background task execution

Container:
  - Docker image: accunode:worker-latest
  - No external ports
  - Environment: Production
  - Restart: always

Celery_Config:
  - Concurrency: 4
  - Prefetch multiplier: 1
  - Task time limit: 300 seconds
  - Max tasks per child: 50
```

## **Database Configuration**
```yaml
# Phase 1: Startup
Instance_Class: db.t3.micro
vCPU: 1
RAM: 1GB
Storage: 20GB GP2
Multi_AZ: false
Backup_Retention: 1 day
Read_Replica: false

# Phase 2: Growth  
Instance_Class: db.t3.small
vCPU: 1
RAM: 2GB
Storage: 50GB GP2
Multi_AZ: false
Backup_Retention: 7 days
Read_Replica: false

# Phase 3: Scale
Instance_Class: db.t3.medium
vCPU: 2  
RAM: 4GB
Storage: 100GB GP2
Multi_AZ: true (optional)
Backup_Retention: 7 days
Read_Replica: true (optional +$65/month)
```

## **Redis Configuration**
```yaml
# Phase 1: Startup
Node_Type: cache.t3.micro
vCPU: 1
RAM: 0.5GB
Use_Case: Task queue + session cache

# Phase 2+: Growth
Node_Type: cache.t3.small
vCPU: 1  
RAM: 1.37GB
Use_Case: High-throughput task queue
```

---

# **🚀 Deployment Process**

## **Step 1: Infrastructure Setup**
```bash
# 1. Create VPC and Networking
aws ec2 create-vpc --cidr-block 10.0.0.0/16
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24  # Public
aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.2.0/24  # Private
aws ec2 create-internet-gateway
aws ec2 create-nat-gateway

# 2. Create Security Groups
aws ec2 create-security-group --group-name accunode-alb-sg
aws ec2 create-security-group --group-name accunode-api-sg  
aws ec2 create-security-group --group-name accunode-worker-sg
aws ec2 create-security-group --group-name accunode-db-sg

# 3. Create Database
aws rds create-db-instance \
  --db-instance-identifier accunode-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --master-username dbadmin \
  --master-user-password $DB_PASSWORD \
  --allocated-storage 20

# 4. Create Redis Cluster  
aws elasticache create-cache-cluster \
  --cache-cluster-id accunode-redis \
  --cache-node-type cache.t3.micro \
  --engine redis

# 5. Create S3 Bucket
aws s3 mb s3://accunode-ml-models-prod
```

## **Step 2: Container Images**
```bash
# Build API Container
cat > Dockerfile.api << EOF
FROM python:3.11-slim
WORKDIR /app
COPY requirements.prod.txt .
RUN pip install -r requirements.prod.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
EOF

# Build Worker Container  
cat > Dockerfile.worker << EOF
FROM python:3.11-slim
WORKDIR /app  
COPY requirements.prod.txt .
RUN pip install -r requirements.prod.txt
COPY . .
CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
EOF

# Push to ECR
aws ecr create-repository --repository-name accunode/api
aws ecr create-repository --repository-name accunode/worker

docker build -f Dockerfile.api -t accunode:api .
docker build -f Dockerfile.worker -t accunode:worker .

docker tag accunode:api $ECR_URI/accunode/api:latest
docker tag accunode:worker $ECR_URI/accunode/worker:latest

docker push $ECR_URI/accunode/api:latest
docker push $ECR_URI/accunode/worker:latest
```

## **Step 3: Launch Template Configuration**
```bash
# API Server Launch Template
cat > api-launch-template.json << EOF
{
  "LaunchTemplateName": "accunode-api-template",
  "LaunchTemplateData": {
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "t3.small",
    "SecurityGroupIds": ["$API_SG_ID"],
    "UserData": "$(base64 -w 0 api-userdata.sh)",
    "TagSpecifications": [
      {
        "ResourceType": "instance", 
        "Tags": [
          {"Key": "Name", "Value": "accunode-api"},
          {"Key": "Type", "Value": "api-server"}
        ]
      }
    ]
  }
}
EOF

# Worker Server Launch Template
cat > worker-launch-template.json << EOF  
{
  "LaunchTemplateName": "accunode-worker-template",
  "LaunchTemplateData": {
    "ImageId": "ami-0abcdef1234567890",
    "InstanceType": "t3.small", 
    "SecurityGroupIds": ["$WORKER_SG_ID"],
    "UserData": "$(base64 -w 0 worker-userdata.sh)",
    "TagSpecifications": [
      {
        "ResourceType": "instance",
        "Tags": [
          {"Key": "Name", "Value": "accunode-worker"}, 
          {"Key": "Type", "Value": "worker-server"}
        ]
      }
    ]
  }
}
EOF
```

## **Step 4: Auto Scaling Groups**
```bash
# Create API Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name accunode-api-asg \
  --launch-template LaunchTemplateName=accunode-api-template,Version=\$Latest \
  --min-size 2 \
  --max-size 4 \
  --desired-capacity 2 \
  --target-group-arns $API_TARGET_GROUP_ARN \
  --vpc-zone-identifier "$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2"

# Create Worker Auto Scaling Group  
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name accunode-worker-asg \
  --launch-template LaunchTemplateName=accunode-worker-template,Version=\$Latest \
  --min-size 2 \
  --max-size 6 \
  --desired-capacity 2 \
  --vpc-zone-identifier "$PRIVATE_SUBNET_1,$PRIVATE_SUBNET_2"
```

## **Step 5: Load Balancer Setup**
```bash
# Create Application Load Balancer
aws elbv2 create-load-balancer \
  --name accunode-alb \
  --subnets $PUBLIC_SUBNET_1 $PUBLIC_SUBNET_2 \
  --security-groups $ALB_SG_ID

# Create Target Group for API servers
aws elbv2 create-target-group \
  --name accunode-api-targets \
  --protocol HTTP \
  --port 8000 \
  --vpc-id $VPC_ID \
  --health-check-path /health \
  --health-check-interval-seconds 30

# Create Listener
aws elbv2 create-listener \
  --load-balancer-arn $ALB_ARN \
  --protocol HTTP \
  --port 80 \
  --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN
```

---

# **📊 Monitoring & Alerts**

## **CloudWatch Metrics**
```bash
# API Server Metrics:
- CPUUtilization
- MemoryUtilization  
- NetworkIn/NetworkOut
- Custom: ActiveConnections
- Custom: ResponseTime

# Worker Server Metrics:
- CPUUtilization
- MemoryUtilization
- Custom: TasksProcessed
- Custom: QueueLength
- Custom: ErrorRate

# Database Metrics:
- CPUUtilization
- DatabaseConnections
- FreeableMemory
- ReadLatency/WriteLatency

# Redis Metrics:
- CPUUtilization
- CurrConnections
- CmdLatency
- EvictedKeys
```

## **Scaling Policies**
```bash
# API Server Scale-Up Policy
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name accunode-api-asg \
  --policy-name api-scale-up \
  --policy-type TargetTrackingScaling \
  --target-tracking-configuration '{
    "TargetValue": 70.0,
    "PredefinedMetricSpecification": {
      "PredefinedMetricType": "ASGAverageCPUUtilization"
    }
  }'

# Worker Server Scale-Up Policy  
aws autoscaling put-scaling-policy \
  --auto-scaling-group-name accunode-worker-asg \
  --policy-name worker-scale-up \
  --policy-type StepScaling \
  --step-adjustments MetricIntervalLowerBound=0,MetricIntervalUpperBound=20,ScalingAdjustment=1
```

## **CloudWatch Alarms**
```bash
# High API Response Time Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "AccuNode-HighResponseTime" \
  --alarm-description "API response time > 500ms" \
  --metric-name TargetResponseTime \
  --namespace AWS/ApplicationELB \
  --statistic Average \
  --period 300 \
  --threshold 0.5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 2

# High Queue Length Alarm
aws cloudwatch put-metric-alarm \
  --alarm-name "AccuNode-HighQueueLength" \
  --alarm-description "Redis queue length > 50 tasks" \
  --metric-name QueueLength \
  --namespace AccuNode/Workers \
  --statistic Average \
  --period 300 \
  --threshold 50 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

---

# **🔒 Security Configuration**

## **Security Groups**
```bash
# ALB Security Group (Internet-facing)
Port 80: 0.0.0.0/0          # HTTP from internet
Port 443: 0.0.0.0/0         # HTTPS from internet (optional)

# API Security Group  
Port 8000: ALB_SG_ID        # HTTP from ALB only
Port 22: ADMIN_IP           # SSH for maintenance

# Worker Security Group
Port 22: ADMIN_IP           # SSH for maintenance  
Outbound: All               # Access to Redis, RDS, S3

# Database Security Group
Port 5432: API_SG_ID        # PostgreSQL from API servers
Port 5432: WORKER_SG_ID     # PostgreSQL from workers

# Redis Security Group  
Port 6379: API_SG_ID        # Redis from API servers
Port 6379: WORKER_SG_ID     # Redis from workers
```

## **IAM Roles**
```bash
# EC2 Instance Role for API Servers
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow", 
      "Action": [
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/accunode/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::accunode-ml-models-prod/*"
    }
  ]
}

# EC2 Instance Role for Worker Servers  
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:GetParameter", 
        "ssm:GetParameters"
      ],
      "Resource": "arn:aws:ssm:*:*:parameter/accunode/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::accunode-ml-models-prod/*"
    }
  ]
}
```

---

# **🎯 Performance Targets**

## **Response Time SLAs**
```bash
API Endpoints:
- Authentication: <100ms (95th percentile)
- Company CRUD: <200ms (95th percentile)  
- Prediction queries: <300ms (95th percentile)
- File upload: <500ms (95th percentile)

Background Tasks:
- Single company prediction: <30 seconds
- Bulk upload (100 companies): <5 minutes
- Bulk upload (1000 companies): <30 minutes
```

## **Availability Targets**
```bash
System Availability: 99.5% uptime
- API servers: 99.9% (redundant)
- Worker processing: 99.0% (auto-recovery)
- Database: 99.9% (AWS managed)
- Redis: 99.5% (AWS managed)

Scalability Targets:
- 500 concurrent users: Phase 1 ($109/month)
- 1200 concurrent users: Phase 2 ($169/month)  
- 2000+ concurrent users: Phase 3 ($230/month)
```

---

# **🛠️ Maintenance & Operations**

## **Deployment Strategy**
```bash
# Blue-Green Deployment for API servers:
1. Deploy new version to standby auto-scaling group
2. Health check new instances
3. Switch ALB target group to new instances
4. Terminate old instances

# Rolling Update for Worker servers:  
1. Deploy new version to 50% of workers
2. Monitor task processing
3. Deploy to remaining 50% of workers
4. Monitor full fleet
```

## **Backup Strategy**
```bash
Database Backups:
- Automated daily backups (1-7 day retention)
- Manual snapshots before major releases
- Point-in-time recovery enabled

Application Backups:
- Container images tagged with git commit SHA
- Configuration stored in Parameter Store
- ML models versioned in S3
```

## **Disaster Recovery**
```bash
RTO (Recovery Time Objective): 30 minutes
RPO (Recovery Point Objective): 1 hour

Recovery Process:
1. Launch new infrastructure in backup region
2. Restore database from latest snapshot
3. Deploy latest application containers  
4. Update DNS to point to new region
5. Validate all services operational
```

---

# **📈 Growth Planning**

## **Scaling Timeline**
```bash
Month 1-3: Phase 1 ($109/month)
- 500-800 users
- 2 API + 2 Worker servers
- Basic monitoring

Month 4-8: Phase 2 ($169/month)  
- 800-1200 users
- 3 API + 4 Worker servers
- Enhanced monitoring + alerting

Month 9+: Phase 3 ($230/month)
- 1200-2000+ users  
- 4 API + 6 Worker servers
- Full observability stack
```

## **Future Enhancements**
```bash
When Revenue Supports It:
- Multi-region deployment (+$200/month)
- Database read replicas (+$65/month)
- ElastiCache cluster mode (+$50/month)  
- Enhanced monitoring (DataDog/NewRelic) (+$100/month)
- CI/CD pipeline automation (+$50/month)
```

---

# **✅ Success Metrics**

## **Technical KPIs**
- API response time p95 < 300ms
- System uptime > 99.5%
- Worker queue length < 20 tasks average
- Database CPU < 70% average
- Cost per user < $0.15/month

## **Business KPIs**  
- User satisfaction > 4.5/5
- Feature adoption > 80%
- Customer support tickets < 5/week
- Revenue growth > 20% monthly
- Churn rate < 5% monthly

---

**🚀 This architecture provides AccuNode with a robust, scalable, and cost-effective foundation that grows with your business while maintaining simplicity and reliability.**
