# 🛠️ **AccuNode AWS Deployment Troubleshooting Guide**

## **Common Issues & Solutions**

---

## **🔴 PHASE 1 ISSUES: Infrastructure Setup**

### **Issue: AWS CLI Permission Denied**
```bash
# Error: User: arn:aws:iam::123456789:user/xxx is not authorized to perform: ec2:CreateVpc
# Solution: Ensure IAM user has required permissions
aws iam list-attached-user-policies --user-name your-username
aws iam attach-user-policy --user-name your-username --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

### **Issue: VPC Creation Fails**
```bash
# Error: The maximum number of VPCs has been reached
# Solution: Check existing VPCs and delete unused ones
aws ec2 describe-vpcs --query 'Vpcs[*].[VpcId,State,Tags[?Key==`Name`].Value|[0]]' --output table

# Delete unused VPC
aws ec2 delete-vpc --vpc-id vpc-xxxxx
```

### **Issue: RDS Creation Fails - Insufficient DB Instance Capacity**
```bash
# Error: Insufficient db instance capacity
# Solution: Try different availability zone or instance type
aws rds create-db-instance \
  --db-instance-identifier default-rate-db \
  --db-instance-class db.t3.micro \
  --availability-zone us-east-1b  # Try different AZ
```

### **Issue: ElastiCache Creation Fails**
```bash
# Error: Cache subnet group doesn't exist
# Solution: Ensure subnet group was created successfully
aws elasticache describe-cache-subnet-groups --cache-subnet-group-name default-rate-redis-subnet-group

# Recreate if missing
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name default-rate-redis-subnet-group \
  --cache-subnet-group-description "Subnet group for Default Rate Redis" \
  --subnet-ids $PRIVATE_SUBNET_1 $PRIVATE_SUBNET_2
```

---

## **🔴 PHASE 2 ISSUES: Database & Storage**

### **Issue: Database Connection Timeout**
```bash
# Error: Connection timeout to RDS
# Check security group rules
aws ec2 describe-security-groups --group-ids $RDS_SG_ID

# Verify database is running
aws rds describe-db-instances --db-instance-identifier default-rate-db --query 'DBInstances[0].DBInstanceStatus'

# Test connection from local (if debugging)
psql -h $DB_ENDPOINT -U dbadmin -d postgres -c "SELECT 1;"
```

### **Issue: S3 Upload Permission Denied**
```bash
# Error: Access Denied when uploading to S3
# Check bucket policy and IAM permissions
aws s3api get-bucket-policy --bucket $BUCKET_NAME

# Fix permissions
aws iam attach-user-policy --user-name your-username --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess
```

### **Issue: Parameter Store Access Denied**
```bash
# Error: User is not authorized to perform: ssm:PutParameter
# Solution: Add SSM permissions
aws iam attach-user-policy --user-name your-username --policy-arn arn:aws:iam::aws:policy/AmazonSSMFullAccess
```

---

## **🔴 PHASE 3 ISSUES: Container Deployment**

### **Issue: ECR Push Permission Denied**
```bash
# Error: no basic auth credentials
# Solution: Re-authenticate with ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.us-east-1.amazonaws.com
```

### **Issue: Docker Build Fails**
```bash
# Error: Cannot build Docker image
# Check Dockerfile and requirements
docker build -t default-rate-app . --no-cache

# Check if all files exist
ls -la requirements.prod.txt
ls -la app/
ls -la start.sh
```

### **Issue: ECS Task Definition Registration Fails**
```bash
# Error: Invalid task definition
# Validate JSON syntax
cat task-definition.json | jq .

# Check IAM role ARNs exist
aws iam get-role --role-name ecsTaskExecutionRole
aws iam get-role --role-name ecsTaskRole
```

---

## **🔴 PHASE 4 ISSUES: ECS Service**

### **Issue: ECS Service Fails to Start**
```bash
# Check service events
aws ecs describe-services --cluster default-rate-cluster --services default-rate-service --query 'services[0].events'

# Check task status
aws ecs list-tasks --cluster default-rate-cluster --service-name default-rate-service
aws ecs describe-tasks --cluster default-rate-cluster --tasks TASK_ARN
```

### **Issue: ECS Tasks Keep Stopping**
```bash
# Common causes and solutions:

# 1. Health check failures
# Check application logs
aws logs tail /ecs/default-rate --follow

# 2. Memory/CPU limits
# Increase task definition resources
aws ecs register-task-definition --family default-rate-task --cpu 1024 --memory 2048 [...]

# 3. Missing environment variables
# Verify parameters exist
aws ssm get-parameter --name "/default-rate/database-url"
aws ssm get-parameter --name "/default-rate/redis-url"
```

### **Issue: Load Balancer Health Checks Failing**
```bash
# Check target group health
aws elbv2 describe-target-health --target-group-arn $TARGET_GROUP_ARN

# Test health endpoint directly
curl -f http://TASK_IP:8000/health

# Check ECS task network settings
aws ecs describe-tasks --cluster default-rate-cluster --tasks TASK_ARN --query 'tasks[0].attachments[0].details'
```

---

## **🔴 PHASE 5 ISSUES: SSL & Domain**

### **Issue: SSL Certificate Validation Stuck**
```bash
# Check certificate status
aws acm describe-certificate --certificate-arn $CERT_ARN --query 'Certificate.DomainValidationOptions'

# Get DNS validation records
aws acm describe-certificate --certificate-arn $CERT_ARN --query 'Certificate.DomainValidationOptions[0].ResourceRecord'

# Add CNAME record to your DNS provider manually
```

### **Issue: HTTPS Listener Creation Fails**
```bash
# Error: Certificate not validated
# Wait for certificate validation first
aws acm describe-certificate --certificate-arn $CERT_ARN --query 'Certificate.Status'

# Should return "ISSUED" before proceeding
```

---

## **🔴 APPLICATION ISSUES**

### **Issue: Application Won't Start - Import Errors**
```bash
# Check application logs for Python import errors
aws logs filter-events --log-group-name /ecs/default-rate --filter-pattern "ImportError"

# Common fixes:
# 1. Missing dependencies in requirements.prod.txt
# 2. Wrong PYTHONPATH in container
# 3. Missing app/__init__.py files
```

### **Issue: Database Migration Fails**
```bash
# Error: relation "users" does not exist
# Run database migrations
# Connect to ECS task and run:
docker exec -it CONTAINER_ID python -c "from app.core.database import create_tables; create_tables()"

# Or add to startup script
```

### **Issue: ML Models Not Loading**
```bash
# Check S3 permissions and model files
aws s3 ls s3://$BUCKET_NAME/models/

# Verify ECS task role has S3 access
aws iam list-attached-role-policies --role-name ecsTaskRole

# Check application logs
aws logs filter-events --log-group-name /ecs/default-rate --filter-pattern "ML Models"
```

### **Issue: Redis Connection Fails**
```bash
# Check Redis cluster status
aws elasticache describe-cache-clusters --cache-cluster-id default-rate-redis --show-cache-node-info

# Verify security group allows ECS access
aws ec2 describe-security-groups --group-ids $REDIS_SG_ID

# Test Redis connectivity from ECS task
# Connect to ECS task: 
redis-cli -h $REDIS_ENDPOINT -p 6379 ping
```

---

## **🔴 PERFORMANCE ISSUES**

### **Issue: Slow Response Times**
```bash
# Check ECS task resources
aws ecs describe-services --cluster default-rate-cluster --services default-rate-service

# Monitor CPU/Memory usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=default-rate-service Name=ClusterName,Value=default-rate-cluster \
  --start-time 2025-10-01T00:00:00Z \
  --end-time 2025-10-01T23:59:59Z \
  --period 300 \
  --statistics Average

# Scale up if needed
aws ecs update-service --cluster default-rate-cluster --service default-rate-service --desired-count 3
```

### **Issue: Database Performance Issues**
```bash
# Check RDS performance
aws rds describe-db-instances --db-instance-identifier default-rate-db --query 'DBInstances[0].DBInstanceStatus'

# Enable Performance Insights (if not enabled)
aws rds modify-db-instance \
  --db-instance-identifier default-rate-db \
  --enable-performance-insights \
  --apply-immediately
```

---

## **🔴 CI/CD ISSUES**

### **Issue: GitHub Actions Deployment Fails**
```bash
# Check GitHub secrets are set correctly:
# AWS_ACCESS_KEY_ID
# AWS_SECRET_ACCESS_KEY  
# AWS_ACCOUNT_ID

# Verify permissions for GitHub user
aws sts get-caller-identity

# Check ECS service deployment status
aws ecs describe-services --cluster default-rate-cluster --services default-rate-service --query 'services[0].deployments'
```

---

## **🛠️ DEBUGGING COMMANDS**

### **Get All Resource Information**
```bash
# Save current state to file
cat > debug_info.txt << EOF
VPC_ID: $(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=default-rate-vpc" --query 'Vpcs[0].VpcId' --output text)
RDS_STATUS: $(aws rds describe-db-instances --db-instance-identifier default-rate-db --query 'DBInstances[0].DBInstanceStatus' --output text)
REDIS_STATUS: $(aws elasticache describe-cache-clusters --cache-cluster-id default-rate-redis --query 'CacheClusters[0].CacheClusterStatus' --output text)
ECS_SERVICE: $(aws ecs describe-services --cluster default-rate-cluster --services default-rate-service --query 'services[0].runningCount' --output text)
ALB_STATE: $(aws elbv2 describe-load-balancers --names default-rate-alb --query 'LoadBalancers[0].State.Code' --output text)
EOF

cat debug_info.txt
```

### **Test Complete Application Stack**
```bash
# Test database connectivity
aws ssm get-parameter --name "/default-rate/database-url" --with-decryption --query 'Parameter.Value' --output text | xargs -I {} psql {} -c "SELECT 1;"

# Test Redis connectivity  
aws ssm get-parameter --name "/default-rate/redis-url" --with-decryption --query 'Parameter.Value' --output text | xargs -I {} redis-cli -u {} ping

# Test application health
curl -f http://$ALB_DNS/health

# Test API endpoints
curl -f http://$ALB_DNS/docs
```

---

## **🆘 EMERGENCY PROCEDURES**

### **Complete Service Restart**
```bash
# Stop all tasks
aws ecs update-service --cluster default-rate-cluster --service default-rate-service --desired-count 0
aws ecs wait services-stable --cluster default-rate-cluster --services default-rate-service

# Start service
aws ecs update-service --cluster default-rate-cluster --service default-rate-service --desired-count 1
aws ecs wait services-stable --cluster default-rate-cluster --services default-rate-service
```

### **Clean Deployment (Nuclear Option)**
```bash
# Delete ECS service
aws ecs update-service --cluster default-rate-cluster --service default-rate-service --desired-count 0
aws ecs delete-service --cluster default-rate-cluster --service default-rate-service

# Redeploy
aws ecs create-service --cli-input-json file://service-definition.json
```

### **Cost Control Emergency**
```bash
# Stop everything to avoid costs
aws ecs update-service --cluster default-rate-cluster --service default-rate-service --desired-count 0
aws rds stop-db-instance --db-instance-identifier default-rate-db
aws elasticache delete-cache-cluster --cache-cluster-id default-rate-redis
```

**💡 Pro Tip: Always check CloudWatch logs first - most issues show up in the application logs with clear error messages.**
