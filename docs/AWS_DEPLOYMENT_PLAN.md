# 🚀 **Core AWS Deployment Plan - Default Rate Backend**

## 📋 **Essential Components Only**

This plan focuses on the **minimum viable AWS infrastructure** to deploy your multi-tenant FastAPI application cost-effectively.

---

## **Phase 1: Core Infrastructure (Week 1)**

### **1.1 Network Setup (Minimal)**
```yaml
VPC Configuration:
- VPC: 10.0.0.0/16 (us-east-1)
- Public Subnets: 10.0.1.0/24, 10.0.2.0/24 (2 AZs)
- Private Subnets: 10.0.3.0/24, 10.0.4.0/24 (2 AZs)
- Internet Gateway + NAT Gateway (1 only)

Security Groups:
- ALB-SG: 80,443 from internet
- ECS-SG: 8000 from ALB, 5432 to RDS, 6379 to Redis
- RDS-SG: 5432 from ECS only
- Redis-SG: 6379 from ECS only
```

### **1.2 Database (Essential)**
```yaml
RDS PostgreSQL:
- Instance: db.t3.micro (FREE tier eligible)
- Storage: 20GB (FREE tier)
- Single-AZ deployment (cost saving)
- Automated backups: 7 days
- No Multi-AZ (add later if needed)

Cost: FREE first year, then $15/month
```

### **1.3 Redis Cache (Essential)**
```yaml
ElastiCache Redis:
- Instance: cache.t3.micro 
- Single node (no replication initially)
- VPC: Private subnet

Cost: $11/month
```

### **1.4 ML Models Storage (Essential)**
```yaml
S3 Bucket:
- Name: default-rate-ml-models-prod
- Standard storage class
- No versioning initially
- Upload your existing model files

Cost: $2/month
```

---

## **Phase 2: Container Deployment (Week 2)**

### **2.1 Container Registry (Essential)**
```bash
# Create one ECR repository
aws ecr create-repository --repository-name default-rate-app

# Build and push single container
docker build -t default-rate-app .
docker tag default-rate-app:latest $ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/default-rate-app:latest
docker push $ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/default-rate-app:latest
```

### **2.2 ECS Setup (Minimal)**
```yaml
ECS Cluster: default-rate-cluster (Fargate)

Single Service Configuration:
- Service Name: default-rate-service
- Task Definition: default-rate-task
- Min Tasks: 1
- Max Tasks: 5 (auto-scaling)
- CPU: 512 (0.5 vCPU)
- Memory: 1024 (1GB)
```

### **2.3 Task Definition (Combined API + Workers)**
```json
{
  "family": "default-rate-task",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskRole",
  "containerDefinitions": [{
    "name": "app",
    "image": "ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/default-rate-app:latest",
    "portMappings": [{"containerPort": 8000}],
    "environment": [
      {"name": "ENVIRONMENT", "value": "production"},
      {"name": "S3_MODELS_BUCKET", "value": "default-rate-ml-models-prod"}
    ],
    "secrets": [
      {"name": "DATABASE_URL", "valueFrom": "/default-rate/database-url"},
      {"name": "REDIS_URL", "valueFrom": "/default-rate/redis-url"},
      {"name": "SECRET_KEY", "valueFrom": "/default-rate/secret-key"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/default-rate",
        "awslogs-region": "us-east-1"
      }
    },
    "healthCheck": {
      "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
      "interval": 30,
      "timeout": 10,
      "retries": 3
    }
  }]
}
```

---

## **Phase 3: Load Balancer & SSL (Week 3)**

### **3.1 Application Load Balancer (Essential)**
```yaml
ALB Configuration:
- Name: default-rate-alb
- Scheme: Internet-facing
- Subnets: Public subnets
- Security Group: ALB-SG

Target Group:
- Protocol: HTTP, Port: 8000
- Health Check: /health
- Target: ECS service

Listeners:
- HTTP (80): Redirect to HTTPS
- HTTPS (443): Forward to target group
```

### **3.2 SSL Certificate (Free)**
```yaml
AWS Certificate Manager:
- Domain: yourdomain.com
- Validation: DNS
- Auto-renewal: Yes
- Cost: FREE
```

### **3.3 Route 53 (Optional - Use existing DNS)**
```yaml
If you have existing domain:
- Create A record pointing to ALB
- Skip Route 53 costs

If using Route 53:
- Hosted zone: $0.50/month
- DNS queries: minimal cost
```

---

## **Phase 4: Auto-Scaling (Essential)**

### **4.1 ECS Service Auto-Scaling**
```yaml
Target Tracking Scaling:
- Metric: CPU Utilization
- Target: 70%
- Scale out cooldown: 300 seconds
- Scale in cooldown: 300 seconds

Min Capacity: 1 task
Max Capacity: 5 tasks

Simple and effective scaling
```

### **4.2 Custom Celery Scaling (Code Update)**
```python
# Update app/services/auto_scaling_service.py
import boto3

class AWSAutoScalingService:
    def __init__(self):
        self.ecs_client = boto3.client('ecs')
        self.cluster_name = "default-rate-cluster"
        self.service_name = "default-rate-service"
    
    async def scale_service(self, desired_count: int):
        """Scale ECS service directly"""
        try:
            self.ecs_client.update_service(
                cluster=self.cluster_name,
                service=self.service_name,
                desiredCount=desired_count
            )
            return True
        except Exception as e:
            logger.error(f"Scaling failed: {e}")
            return False
    
    async def get_current_task_count(self):
        """Get current running tasks"""
        response = self.ecs_client.describe_services(
            cluster=self.cluster_name,
            services=[self.service_name]
        )
        return response['services'][0]['runningCount']
```

---

## **Phase 5: Monitoring (Minimal)**

### **5.1 CloudWatch Logs (Essential)**
```yaml
Log Groups:
- /ecs/default-rate (retention: 7 days)

Cost: $5/month for basic logging
```

### **5.2 Basic Alarms (Essential)**
```yaml
Critical Alarms Only:
1. ECS Service Health
   - Metric: Running task count < 1
   - Action: SNS notification

2. ALB Health  
   - Metric: Target health < 1
   - Action: SNS notification

3. Database Health
   - Metric: Database connections
   - Action: SNS notification

Cost: $3/month (3 alarms)
```

---

## **Phase 6: Secrets Management (Essential)**

### **6.1 AWS Systems Manager Parameter Store**
```bash
# Store secrets (FREE for standard parameters)
aws ssm put-parameter --name "/default-rate/database-url" --value "postgresql://..." --type "SecureString"
aws ssm put-parameter --name "/default-rate/redis-url" --value "redis://..." --type "SecureString"  
aws ssm put-parameter --name "/default-rate/secret-key" --value "your-secret-key" --type "SecureString"

Cost: FREE for standard parameters
```

---

## **Phase 7: Deployment Pipeline (Simple)**

### **7.1 GitHub Actions (Basic)**
```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [prod]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Configure AWS
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Login to ECR
      run: aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com

    - name: Build and push
      run: |
        docker build -t default-rate-app .
        docker tag default-rate-app:latest ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/default-rate-app:latest
        docker push ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.us-east-1.amazonaws.com/default-rate-app:latest

    - name: Deploy to ECS
      run: |
        aws ecs update-service --cluster default-rate-cluster --service default-rate-service --force-new-deployment
        aws ecs wait services-stable --cluster default-rate-cluster --services default-rate-service
```

---

## **💰 Minimal Cost Breakdown**

### **Monthly Costs (Optimized)**

#### **Year 1 (With Free Tier):**
```yaml
ECS Fargate (1-2 tasks avg): $35/month
RDS t3.micro: FREE (first year)
ElastiCache t3.micro: $11/month
ALB: $16/month
NAT Gateway: $32/month
S3 Storage: $2/month
CloudWatch: $8/month
Certificate Manager: FREE
Parameter Store: FREE

Total Year 1: $104/month
```

#### **Year 2 (After Free Tier):**
```yaml
ECS Fargate: $35/month
RDS t3.micro: $15/month
ElastiCache: $11/month  
ALB: $16/month
NAT Gateway: $32/month
S3 Storage: $2/month
CloudWatch: $8/month

Total Year 2: $119/month
```

### **Cost Optimization Tips:**
```yaml
1. Use Fargate Spot (50% savings): $17.50/month instead of $35
2. Reserved instances after 6 months (30% savings)
3. Turn off NAT Gateway if not needed ($32 savings)
4. Use CloudFront for static content (optional)

Optimized Total: $55-85/month possible
```

---

## **🚀 Deployment Steps (Simplified)**

### **Week 1: Setup**
1. **Create AWS account** and set up billing alerts
2. **Create VPC** with public/private subnets  
3. **Set up RDS PostgreSQL** and migrate data
4. **Set up ElastiCache Redis**
5. **Create S3 bucket** and upload ML models

### **Week 2: Deploy Application**
1. **Create ECR repository**
2. **Build and push Docker image**
3. **Create ECS cluster and service**  
4. **Test application health**

### **Week 3: Production Ready**
1. **Set up ALB with SSL certificate**
2. **Configure domain/DNS**
3. **Enable auto-scaling**
4. **Set up basic monitoring**
5. **Go live!**

### **Week 4: CI/CD**
1. **Set up GitHub Actions**
2. **Configure secrets**
3. **Test deployment pipeline**
4. **Monitor and optimize**

---

## **⚠️ What We're NOT Including (To Add Later)**

```yaml
Not Included (Save $500+/month):
- Multi-AZ database (add when needed)
- Advanced monitoring/APM tools
- WAF (Web Application Firewall)  
- Multiple environments (staging)
- Redis replication
- Advanced security features
- Detailed dashboards
- X-Ray tracing

Add These Later When:
- You have consistent traffic (Multi-AZ)
- You need advanced security (WAF)
- You want detailed monitoring (APM tools)
- You scale beyond 10,000 users
```

---

## **🎯 Success Criteria**

### **After Deployment You'll Have:**
✅ **Scalable FastAPI application** running on AWS  
✅ **PostgreSQL database** with automated backups  
✅ **Redis caching** for Celery workers  
✅ **HTTPS/SSL** with free certificate  
✅ **Auto-scaling** based on CPU usage  
✅ **CI/CD pipeline** for easy deployments  
✅ **Health monitoring** with basic alerts  
✅ **Cost under $120/month** (after free tier)

### **Performance Expectations:**
- **Response Time**: < 500ms for API calls
- **Uptime**: 99.5%+ with auto-scaling  
- **Scalability**: Handle 1-5 concurrent users easily
- **ML Processing**: Same speed as current setup
- **Background Jobs**: Celery workers in same container

**This minimal setup gives you production-ready AWS deployment with room to grow, while keeping costs under $120/month after the first year!**
