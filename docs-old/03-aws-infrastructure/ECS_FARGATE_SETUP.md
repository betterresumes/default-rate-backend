# ☁️ ECS Fargate Setup Documentation

## 📋 **Table of Contents**
1. [ECS Fargate Overview](#ecs-fargate-overview)
2. [Infrastructure Architecture](#infrastructure-architecture)
3. [Container Configuration](#container-configuration)
4. [Service Configuration](#service-configuration)
5. [Auto Scaling Setup](#auto-scaling-setup)
6. [Load Balancer Configuration](#load-balancer-configuration)
7. [Networking & Security](#networking--security)
8. [Monitoring & Logging](#monitoring--logging)
9. [Deployment Process](#deployment-process)
10. [Troubleshooting](#troubleshooting)

---

## ☁️ **ECS Fargate Overview**

AccuNode runs on Amazon ECS Fargate for serverless container orchestration, providing automatic scaling, high availability, and cost optimization without managing EC2 instances.

### **Architecture Benefits**
- **Serverless**: No EC2 instance management required
- **Auto Scaling**: Automatic horizontal and vertical scaling
- **Cost Optimized**: Pay only for resources used
- **High Availability**: Multi-AZ deployment with failover
- **Security**: VPC isolation with task-level IAM roles

### **Resource Specifications**
| Environment | CPU (vCPU) | Memory (GB) | Storage | Min Tasks | Max Tasks |
|-------------|------------|-------------|---------|-----------|-----------|
| **Development** | 0.25 | 0.5 | 20GB | 1 | 2 |
| **Staging** | 0.5 | 1.0 | 30GB | 1 | 3 |
| **Production** | 1.0 | 2.0 | 50GB | 2 | 10 |

---

## 🏗️ **Infrastructure Architecture**

### **ECS Cluster Structure**

```
AccuNode-Cluster
├── FastAPI Service (accunode-api)
│   ├── Task Definition: accunode-api-td
│   ├── Service: accunode-api-service  
│   └── Container: accunode-api-container
├── Celery Worker Service (accunode-worker)
│   ├── Task Definition: accunode-worker-td
│   ├── Service: accunode-worker-service
│   └── Container: accunode-worker-container
└── Redis Service (accunode-redis)
    ├── Task Definition: accunode-redis-td
    ├── Service: accunode-redis-service
    └── Container: accunode-redis-container
```

### **Network Architecture**

```
Internet Gateway
    ↓
Application Load Balancer (Public Subnets)
    ↓
ECS Fargate Services (Private Subnets)
    ↓
RDS PostgreSQL (Private DB Subnets)
```

### **AWS Resource Components**

```yaml
# Core ECS Resources
- ECS Cluster: accunode-cluster-prod
- ECS Services: 
  - accunode-api-service (2-10 tasks)
  - accunode-worker-service (1-5 tasks)
- Task Definitions:
  - accunode-api-td:latest
  - accunode-worker-td:latest
  
# Load Balancing
- Application Load Balancer: accunode-alb-prod
- Target Groups:
  - accunode-api-tg (Port 8000)
  - accunode-health-tg (Port 8000/health)
  
# Networking
- VPC: accunode-vpc-prod (10.0.0.0/16)
- Public Subnets: 2 AZs (10.0.1.0/24, 10.0.2.0/24)
- Private Subnets: 2 AZs (10.0.10.0/24, 10.0.20.0/24)
- DB Subnets: 2 AZs (10.0.30.0/24, 10.0.40.0/24)

# Security
- Security Groups: ECS, ALB, RDS
- IAM Roles: Task Execution, Task Role
- Secrets Manager: Database credentials, API keys
```

---

## 📦 **Container Configuration**

### **FastAPI Container (Main API)**

**Dockerfile:**
```dockerfile
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

# Copy application code
COPY . .

# Create non-root user
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Start command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
```

**Environment Variables:**
```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@rds-endpoint/database
REDIS_URL=redis://accunode-redis-service:6379

# Application Settings
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=${SECRET_KEY_FROM_SECRETS_MANAGER}
JWT_SECRET_KEY=${JWT_SECRET_FROM_SECRETS_MANAGER}

# AWS Configuration
AWS_REGION=us-east-1
AWS_DEFAULT_REGION=us-east-1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Performance
UVICORN_WORKERS=1
UVICORN_MAX_REQUESTS=1000
UVICORN_MAX_REQUESTS_JITTER=100
```

### **Celery Worker Container**

**Dockerfile:**
```dockerfile
FROM python:3.11-slim-bullseye

WORKDIR /app

# Same base setup as FastAPI container
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.prod.txt .
RUN pip install --no-cache-dir -r requirements.prod.txt

COPY . .

RUN adduser --disabled-password --gecos '' celeryuser && \
    chown -R celeryuser:celeryuser /app
USER celeryuser

# Health check for Celery
HEALTHCHECK --interval=60s --timeout=30s --start-period=10s --retries=3 \
  CMD celery -A app.workers.celery_app inspect ping || exit 1

# Start Celery worker
CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
```

---

## ⚙️ **Service Configuration**

### **FastAPI Service Definition**

**Task Definition JSON:**
```json
{
  "family": "accunode-api-td",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "accunode-api-container",
      "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/accunode-api:latest",
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
          "name": "AWS_REGION",
          "value": "us-east-1"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:accunode/database-url"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:accunode/secret-key"
        },
        {
          "name": "JWT_SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:accunode/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/accunode-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": [
          "CMD-SHELL",
          "curl -f http://localhost:8000/health || exit 1"
        ],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### **ECS Service Configuration**

**Service Definition:**
```yaml
ServiceName: accunode-api-service
Cluster: accunode-cluster-prod
TaskDefinition: accunode-api-td:latest
DesiredCount: 2
LaunchType: FARGATE

NetworkConfiguration:
  AwsvpcConfiguration:
    Subnets:
      - subnet-12345678  # Private subnet AZ-1
      - subnet-87654321  # Private subnet AZ-2
    SecurityGroups:
      - sg-ecs-api-12345  # ECS API security group
    AssignPublicIp: DISABLED

LoadBalancers:
  - TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/accunode-api-tg
    ContainerName: accunode-api-container
    ContainerPort: 8000

ServiceRegistries:
  - RegistryArn: arn:aws:servicediscovery:us-east-1:ACCOUNT:service/srv-api
    ContainerName: accunode-api-container
    ContainerPort: 8000

DeploymentConfiguration:
  MaximumPercent: 200
  MinimumHealthyPercent: 50
  
HealthCheckGracePeriodSeconds: 300
EnableExecuteCommand: true
```

---

## 📈 **Auto Scaling Setup**

### **Application Auto Scaling Configuration**

**Target Tracking Policies:**

```yaml
# CPU Utilization Scaling
- PolicyName: accunode-api-cpu-scaling
  PolicyType: TargetTrackingScaling
  TargetTrackingScalingPolicies:
    - TargetValue: 70.0
      ScaleOutCooldown: 300  # 5 minutes
      ScaleInCooldown: 300   # 5 minutes
      MetricSpecifications:
        MetricType: ECSServiceAverageCPUUtilization

# Memory Utilization Scaling  
- PolicyName: accunode-api-memory-scaling
  PolicyType: TargetTrackingScaling
  TargetTrackingScalingPolicies:
    - TargetValue: 80.0
      ScaleOutCooldown: 300
      ScaleInCooldown: 300
      MetricSpecifications:
        MetricType: ECSServiceAverageMemoryUtilization

# ALB Request Count Scaling
- PolicyName: accunode-api-request-scaling
  PolicyType: TargetTrackingScaling
  TargetTrackingScalingPolicies:
    - TargetValue: 1000.0  # Requests per minute per task
      ScaleOutCooldown: 180  # 3 minutes
      ScaleInCooldown: 300   # 5 minutes
      MetricSpecifications:
        MetricType: ALBRequestCountPerTarget
        ResourceLabel: app/accunode-alb-prod/targetgroup/accunode-api-tg
```

### **Scaling Limits**

```yaml
ScalableTarget:
  ServiceNamespace: ecs
  ResourceId: service/accunode-cluster-prod/accunode-api-service
  ScalableDimension: ecs:service:DesiredCount
  MinCapacity: 2      # Minimum tasks
  MaxCapacity: 10     # Maximum tasks
  
# Scaling Metrics Thresholds
Thresholds:
  CPU_High: 70%        # Scale out
  CPU_Low: 30%         # Scale in
  Memory_High: 80%     # Scale out  
  Memory_Low: 40%      # Scale in
  RequestRate_High: 1000/min/task  # Scale out
  RequestRate_Low: 100/min/task    # Scale in
```

### **Custom CloudWatch Alarms**

```yaml
# High Error Rate Alarm
- AlarmName: AccuNode-API-HighErrorRate
  MetricName: HTTPCode_Target_5XX_Count
  Namespace: AWS/ApplicationELB
  Statistic: Sum
  Period: 300
  EvaluationPeriods: 2
  Threshold: 10
  ComparisonOperator: GreaterThanThreshold
  AlarmActions:
    - arn:aws:sns:us-east-1:ACCOUNT:accunode-alerts

# Response Time Alarm  
- AlarmName: AccuNode-API-HighLatency
  MetricName: TargetResponseTime
  Namespace: AWS/ApplicationELB
  Statistic: Average
  Period: 300
  EvaluationPeriods: 2
  Threshold: 2.0  # 2 seconds
  ComparisonOperator: GreaterThanThreshold
```

---

## ⚖️ **Load Balancer Configuration**

### **Application Load Balancer Setup**

```yaml
LoadBalancerName: accunode-alb-prod
Scheme: internet-facing
Type: application
IpAddressType: ipv4

Subnets:
  - subnet-public-1a  # Public subnet AZ-1
  - subnet-public-1b  # Public subnet AZ-2

SecurityGroups:
  - sg-alb-prod-12345

Tags:
  - Key: Environment
    Value: production
  - Key: Application
    Value: accunode
```

### **Target Group Configuration**

```yaml
# Main API Target Group
- TargetGroupName: accunode-api-tg-prod
  Protocol: HTTP
  Port: 8000
  VpcId: vpc-12345678
  TargetType: ip
  
  HealthCheckSettings:
    HealthCheckProtocol: HTTP
    HealthCheckPath: /health
    HealthCheckIntervalSeconds: 30
    HealthCheckTimeoutSeconds: 5
    HealthyThresholdCount: 2
    UnhealthyThresholdCount: 3
    Matcher: '200'
    
  Attributes:
    - Key: deregistration_delay.timeout_seconds
      Value: '30'
    - Key: stickiness.enabled
      Value: 'false'
    - Key: target_group_health.unhealthy_state_routing.minimum_healthy_targets.percentage
      Value: '50'
```

### **Listener Rules**

```yaml
# HTTPS Listener (Port 443)
- Port: 443
  Protocol: HTTPS
  Certificates:
    - CertificateArn: arn:aws:acm:us-east-1:ACCOUNT:certificate/cert-id
  DefaultActions:
    - Type: forward
      TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/accunode-api-tg-prod

  Rules:
    # API Routes
    - Priority: 100
      Conditions:
        - Field: path-pattern
          Values: ['/api/*']
      Actions:
        - Type: forward
          TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/accunode-api-tg-prod
          
    # Health Check Route
    - Priority: 200
      Conditions:
        - Field: path-pattern
          Values: ['/health', '/health/*']
      Actions:
        - Type: forward
          TargetGroupArn: arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/accunode-api-tg-prod

# HTTP Listener (Port 80) - Redirect to HTTPS
- Port: 80
  Protocol: HTTP
  DefaultActions:
    - Type: redirect
      RedirectConfig:
        Protocol: HTTPS
        Port: '443'
        StatusCode: HTTP_301
```

---

## 🔐 **Networking & Security**

### **VPC Configuration**

```yaml
VPC:
  CidrBlock: 10.0.0.0/16
  EnableDnsHostnames: true
  EnableDnsSupport: true
  
Subnets:
  # Public Subnets (ALB)
  PublicSubnet1:
    CidrBlock: 10.0.1.0/24
    AvailabilityZone: us-east-1a
    MapPublicIpOnLaunch: true
    
  PublicSubnet2:
    CidrBlock: 10.0.2.0/24
    AvailabilityZone: us-east-1b
    MapPublicIpOnLaunch: true
    
  # Private Subnets (ECS Tasks)
  PrivateSubnet1:
    CidrBlock: 10.0.10.0/24
    AvailabilityZone: us-east-1a
    
  PrivateSubnet2:
    CidrBlock: 10.0.20.0/24
    AvailabilityZone: us-east-1b
    
  # Database Subnets
  DatabaseSubnet1:
    CidrBlock: 10.0.30.0/24
    AvailabilityZone: us-east-1a
    
  DatabaseSubnet2:
    CidrBlock: 10.0.40.0/24
    AvailabilityZone: us-east-1b

# Internet Gateway
InternetGateway:
  Type: AWS::EC2::InternetGateway
  
# NAT Gateways (for private subnet internet access)
NatGateway1:
  Type: AWS::EC2::NatGateway
  AllocationId: !GetAtt EipNatGateway1.AllocationId
  SubnetId: !Ref PublicSubnet1
  
NatGateway2:
  Type: AWS::EC2::NatGateway
  AllocationId: !GetAtt EipNatGateway2.AllocationId
  SubnetId: !Ref PublicSubnet2
```

### **Security Groups**

```yaml
# ALB Security Group
ALBSecurityGroup:
  GroupName: accunode-alb-sg-prod
  GroupDescription: Security group for AccuNode ALB
  VpcId: !Ref VPC
  SecurityGroupIngress:
    - IpProtocol: tcp
      FromPort: 80
      ToPort: 80
      CidrIp: 0.0.0.0/0
      Description: HTTP from internet
    - IpProtocol: tcp
      FromPort: 443
      ToPort: 443
      CidrIp: 0.0.0.0/0
      Description: HTTPS from internet
      
# ECS Security Group
ECSSecurityGroup:
  GroupName: accunode-ecs-sg-prod
  GroupDescription: Security group for AccuNode ECS tasks
  VpcId: !Ref VPC
  SecurityGroupIngress:
    - IpProtocol: tcp
      FromPort: 8000
      ToPort: 8000
      SourceSecurityGroupId: !Ref ALBSecurityGroup
      Description: HTTP from ALB
    - IpProtocol: tcp
      FromPort: 6379
      ToPort: 6379
      SourceSecurityGroupId: !Ref ECSSecurityGroup
      Description: Redis inter-service communication

# RDS Security Group  
RDSSecurityGroup:
  GroupName: accunode-rds-sg-prod
  GroupDescription: Security group for AccuNode RDS
  VpcId: !Ref VPC
  SecurityGroupIngress:
    - IpProtocol: tcp
      FromPort: 5432
      ToPort: 5432
      SourceSecurityGroupId: !Ref ECSSecurityGroup
      Description: PostgreSQL from ECS tasks
```

### **IAM Roles & Policies**

```yaml
# ECS Task Execution Role
ECSTaskExecutionRole:
  RoleName: accunode-ecs-execution-role
  AssumeRolePolicyDocument:
    Version: '2012-10-17'
    Statement:
      - Effect: Allow
        Principal:
          Service: ecs-tasks.amazonaws.com
        Action: sts:AssumeRole
  ManagedPolicyArns:
    - arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
  Policies:
    - PolicyName: SecretsManagerAccess
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - secretsmanager:GetSecretValue
            Resource:
              - arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:accunode/*

# ECS Task Role (for application permissions)
ECSTaskRole:
  RoleName: accunode-ecs-task-role
  AssumeRolePolicyDocument:
    Version: '2012-10-17'
    Statement:
      - Effect: Allow
        Principal:
          Service: ecs-tasks.amazonaws.com
        Action: sts:AssumeRole
  Policies:
    - PolicyName: S3Access
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - s3:GetObject
              - s3:PutObject
              - s3:DeleteObject
            Resource:
              - arn:aws:s3:::accunode-data-prod/*
    - PolicyName: SESAccess
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - ses:SendEmail
              - ses:SendRawEmail
            Resource: "*"
```

---

## 📊 **Monitoring & Logging**

### **CloudWatch Log Groups**

```yaml
LogGroups:
  # API Application Logs
  - LogGroupName: /ecs/accunode-api
    RetentionInDays: 30
    
  # Celery Worker Logs  
  - LogGroupName: /ecs/accunode-worker
    RetentionInDays: 30
    
  # ALB Access Logs
  - LogGroupName: /aws/applicationloadbalancer/accunode-alb-prod
    RetentionInDays: 14
```

### **Custom CloudWatch Metrics**

```python
# Custom metrics in application code
import boto3

cloudwatch = boto3.client('cloudwatch')

def publish_custom_metrics():
    # Prediction creation rate
    cloudwatch.put_metric_data(
        Namespace='AccuNode/Application',
        MetricData=[
            {
                'MetricName': 'PredictionsCreated',
                'Value': 1,
                'Unit': 'Count',
                'Dimensions': [
                    {
                        'Name': 'Service',
                        'Value': 'API'
                    }
                ]
            }
        ]
    )
    
    # ML Model inference time
    cloudwatch.put_metric_data(
        Namespace='AccuNode/ML',
        MetricData=[
            {
                'MetricName': 'ModelInferenceTime',
                'Value': inference_time_ms,
                'Unit': 'Milliseconds',
                'Dimensions': [
                    {
                        'Name': 'ModelType',
                        'Value': 'Annual'
                    }
                ]
            }
        ]
    )
```

### **CloudWatch Dashboard**

```json
{
  "widgets": [
    {
      "type": "metric",
      "properties": {
        "metrics": [
          ["AWS/ECS", "CPUUtilization", "ServiceName", "accunode-api-service"],
          [".", "MemoryUtilization", ".", "."]
        ],
        "period": 300,
        "stat": "Average",
        "region": "us-east-1",
        "title": "ECS Resource Utilization"
      }
    },
    {
      "type": "metric", 
      "properties": {
        "metrics": [
          ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "app/accunode-alb-prod"],
          [".", "TargetResponseTime", ".", "."],
          [".", "HTTPCode_Target_2XX_Count", ".", "."],
          [".", "HTTPCode_Target_5XX_Count", ".", "."]
        ],
        "period": 300,
        "stat": "Sum",
        "region": "us-east-1",
        "title": "Load Balancer Metrics"
      }
    }
  ]
}
```

---

## 🚀 **Deployment Process**

### **CI/CD Pipeline Integration**

**GitHub Actions Workflow:**
```yaml
name: Deploy to ECS Fargate

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1
          
      - name: Login to ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1
        
      - name: Build and push API image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          ECR_REPOSITORY: accunode-api
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG .
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG
          docker tag $ECR_REGISTRY/$ECR_REPOSITORY:$IMAGE_TAG $ECR_REGISTRY/$ECR_REPOSITORY:latest
          docker push $ECR_REGISTRY/$ECR_REPOSITORY:latest
          
      - name: Update ECS task definition
        id: task-def
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: .aws/task-definition.json
          container-name: accunode-api-container
          image: ${{ steps.login-ecr.outputs.registry }}/accunode-api:${{ github.sha }}
          
      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: ${{ steps.task-def.outputs.task-definition }}
          service: accunode-api-service
          cluster: accunode-cluster-prod
          wait-for-service-stability: true
```

### **Blue/Green Deployment**

```yaml
# CodeDeploy Application for Blue/Green deployment
CodeDeployApplication:
  ApplicationName: accunode-ecs-deploy
  ComputePlatform: ECS
  
CodeDeployDeploymentGroup:
  ApplicationName: !Ref CodeDeployApplication
  DeploymentGroupName: accunode-api-deployment-group
  ServiceRoleArn: arn:aws:iam::ACCOUNT:role/CodeDeployServiceRoleForECS
  
  BlueGreenDeploymentConfiguration:
    TerminateBlueInstancesOnDeploymentSuccess:
      Action: TERMINATE
      TerminationWaitTimeInMinutes: 5
    DeploymentReadyOption:
      ActionOnTimeout: CONTINUE_DEPLOYMENT
    GreenFleetProvisioningOption:
      Action: COPY_AUTO_SCALING_GROUP
      
  LoadBalancerInfo:
    TargetGroupInfoList:
      - Name: accunode-api-tg-prod
        
  AutoRollbackConfiguration:
    Enabled: true
    Events:
      - DEPLOYMENT_FAILURE
      - DEPLOYMENT_STOP_ON_ALARM
```

---

## 🔧 **Troubleshooting**

### **Common Issues & Solutions**

**1. Service Not Starting**
```bash
# Check service events
aws ecs describe-services \
  --cluster accunode-cluster-prod \
  --services accunode-api-service \
  --query 'services[0].events[0:5]'

# Check task definition
aws ecs describe-task-definition \
  --task-definition accunode-api-td:latest

# Check CloudWatch logs
aws logs get-log-events \
  --log-group-name /ecs/accunode-api \
  --log-stream-name ecs/accunode-api-container/TASK-ID
```

**2. Health Check Failures**
```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:us-east-1:ACCOUNT:targetgroup/accunode-api-tg-prod

# Test health endpoint directly
curl -v http://TASK-IP:8000/health
```

**3. Scaling Issues**
```bash
# Check scaling policies
aws application-autoscaling describe-scaling-policies \
  --service-namespace ecs \
  --resource-id service/accunode-cluster-prod/accunode-api-service

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=accunode-api-service \
  --start-time 2023-10-05T12:00:00Z \
  --end-time 2023-10-05T18:00:00Z \
  --period 300 \
  --statistics Average
```

### **Debugging Commands**

```bash
# Execute into running container
aws ecs execute-command \
  --cluster accunode-cluster-prod \
  --task TASK-ARN \
  --container accunode-api-container \
  --interactive \
  --command "/bin/bash"

# View real-time logs
aws logs tail /ecs/accunode-api --follow

# Check service discovery
aws servicediscovery list-services \
  --namespace-id ns-12345678

# Monitor task placement
aws ecs describe-tasks \
  --cluster accunode-cluster-prod \
  --tasks TASK-ARN
```

---

**Last Updated**: October 5, 2023  
**Infrastructure Version**: 2.0
