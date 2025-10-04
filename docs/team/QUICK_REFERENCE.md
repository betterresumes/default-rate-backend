# 🚀 AccuNode Quick Reference Card

## 📊 **At-a-Glance**
- **Account**: AWS 461962182774 (pranit@company.com)
- **Environment**: Production (`prod` branch)
- **Daily Cost**: ~$3.60 USD | Monthly: ~$108 USD
- **Services**: 2 ECS services, RDS, Redis, ALB
- **Auto-Scale**: Max 4 containers (2 API + 2 Worker)

---

## 🔧 **Quick Commands**

### **Deploy**
```bash
git push origin prod  # Automatic deployment via GitHub Actions
```

### **Scale Services**
```bash
# Scale API to 2 instances
aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --desired-count 2

# Scale Worker to 2 instances  
aws ecs update-service --cluster AccuNode-Production --service accunode-worker-service --desired-count 2
```

### **Check Status**
```bash
# Service status
aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service

# Recent logs
aws logs tail /ecs/accunode-api --follow

# Health check
curl -f https://AccuNode-ECS-ALB-761974571.us-east-1.elb.amazonaws.com/health
```

### **Emergency Rollback**
```bash
# Get previous version
PREV_TASK=$(aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service --query 'services[0].deployments[1].taskDefinition' --output text)

# Rollback
aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --task-definition $PREV_TASK
```

---

## 💰 **Cost Breakdown**
| Service | Daily | Monthly | Purpose |
|---------|-------|---------|---------|
| ECS Fargate | $1.38 | $41.40 | App containers |
| RDS PostgreSQL | $0.70 | $21.00 | Database |
| Load Balancer | $0.59 | $17.70 | Traffic routing |
| VPC/Networking | $0.62 | $18.60 | Network infrastructure |
| Redis Cache | $0.31 | $9.30 | Caching |
| ECR Registry | $0.02 | $0.60 | Image storage |

---

## 🎯 **Service Configuration**

### **ECS Services**
- **Cluster**: AccuNode-Production
- **API Service**: accunode-api-service (Port 8000)
- **Worker Service**: accunode-worker-service (Background tasks)
- **Platform**: Fargate (0.25 vCPU, 512MB RAM per task)

### **Auto-Scaling**
- **API**: Min 1, Max 2 (Scale at 70% CPU)
- **Worker**: Min 1, Max 2 (Scale at 60% CPU)
- **Total Max**: 4 containers

### **Database**
- **Instance**: accunode-postgres (db.t3.small)
- **Engine**: PostgreSQL 15.7
- **Storage**: 20GB GP3
- **Backups**: 7 days

### **Cache**
- **Instance**: accunode-redis (cache.t3.micro)
- **Engine**: Redis
- **Purpose**: Session storage, rate limiting

---

## 🔐 **Secrets & Configuration**

### **Parameter Store Secrets**
```bash
/accunode/database-url    # PostgreSQL connection
/accunode/redis-url       # Redis connection  
/accunode/secret-key      # Application secret
```

### **Environment Variables**
```bash
ENVIRONMENT=production
AWS_REGION=us-east-1
DEBUG=false
```

---

## 🚨 **Troubleshooting Checklist**

### **Deployment Issues**
- [ ] Check GitHub Actions workflow status
- [ ] Verify ECR image exists: `aws ecr list-images --repository-name accunode`
- [ ] Check Parameter Store secrets are accessible
- [ ] Review ECS service events: `aws ecs describe-services`

### **Performance Issues**  
- [ ] Check CPU metrics: CloudWatch ECS metrics
- [ ] Review application logs: `aws logs tail /ecs/accunode-api`
- [ ] Verify database connections
- [ ] Check Redis cache hit rates

### **Connection Issues**
- [ ] Test ALB health: `curl -f <ALB-URL>/health`
- [ ] Check security group rules
- [ ] Verify VPC networking
- [ ] Test database connectivity

---

## 📞 **Emergency Contacts**

### **Infrastructure Owner**
- **Name**: Pranit
- **AWS Account**: 461962182774
- **GitHub**: betterresumes/default-rate-backend

### **Key Resources**
- **AWS Console**: [ECS Dashboard](https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/AccuNode-Production)
- **GitHub Actions**: [CI/CD Pipeline](https://github.com/betterresumes/default-rate-backend/actions)
- **Cost Dashboard**: [AWS Billing](https://console.aws.amazon.com/billing/home#/)

---

## 📋 **Daily Operations**

### **Morning Checklist**
- [ ] Check service health status
- [ ] Review overnight logs for errors
- [ ] Verify auto-scaling events
- [ ] Check cost alerts

### **Deployment Process**
1. Create feature branch
2. Make changes and test locally
3. Create PR to `prod` (triggers security scan)
4. Merge PR (triggers full deployment)
5. Monitor deployment in GitHub Actions
6. Verify service health post-deployment

### **Monitoring**
- **Metrics**: CloudWatch ECS dashboard
- **Logs**: `aws logs tail /ecs/accunode-api --follow`
- **Costs**: AWS Cost Explorer
- **Alerts**: CloudWatch alarms

---

*Quick Reference v1.0 | Updated: Oct 4, 2025*
