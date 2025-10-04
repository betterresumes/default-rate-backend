# Common Issues and Solutions

Comprehensive troubleshooting guide for frequently encountered AccuNode issues and their solutions.

## Quick Reference

| Issue Type | Severity | Typical Cause | Quick Fix |
|------------|----------|---------------|-----------|
| API 500 errors | High | Database connection | Check DB connectivity |
| Slow responses | Medium | Model loading | Restart ECS service |
| Authentication failures | High | JWT token issues | Verify token generation |
| Health check failures | Critical | Container startup | Check application logs |
| Memory errors | High | Memory leak | Restart containers |

## Application Issues

### 1. FastAPI Application Won't Start

**Symptoms:**
- Container exits immediately
- ECS task stops with exit code 1
- Health checks fail immediately

**Common Causes:**
```bash
# Check application logs
docker logs container-id
# or
aws logs tail /ecs/accunode-api --follow

# Common error patterns:
# "ModuleNotFoundError: No module named 'app'"
# "ValidationError: field required"
# "Connection refused: database"
```

**Solutions:**

**A. Missing Environment Variables**
```bash
# Check required environment variables
env | grep -E "(DATABASE|REDIS|JWT)"

# Verify Parameter Store values
aws ssm get-parameters --names \
  "/accunode/production/database/host" \
  "/accunode/production/database/password" \
  "/accunode/production/jwt/secret"
```

**B. Database Connection Issues**
```bash
# Test database connectivity from container
docker exec -it container-id sh
apk add postgresql-client
psql -h $DATABASE_HOST -U $DATABASE_USER -d $DATABASE_NAME

# Check security groups allow ECS → RDS traffic
aws ec2 describe-security-groups --group-ids sg-ecs-id sg-rds-id
```

**C. Import Path Issues**
```python
# Verify Python path in container
PYTHONPATH=/app python -c "import app.main"

# Check Dockerfile WORKDIR and module structure
```

### 2. ML Model Loading Failures

**Symptoms:**
- 500 errors on prediction endpoints
- "Model file not found" errors
- Memory allocation errors during startup

**Diagnosis:**
```bash
# Check model files exist
ls -la /app/models/
# Should contain:
# - annual_logistic_model.pkl
# - quarterly_lgb_model.pkl
# - scoring_info.pkl
# - quarterly_scoring_info.pkl

# Check model file sizes
du -h /app/models/*.pkl

# Test model loading
python -c "
import pickle
with open('/app/models/annual_logistic_model.pkl', 'rb') as f:
    model = pickle.load(f)
print('Model loaded successfully')
"
```

**Solutions:**

**A. Missing Model Files**
```bash
# Rebuild Docker image with models
docker build -t accunode/api .

# Verify models are included in image
docker run --rm accunode/api ls -la /app/models/
```

**B. Model File Corruption**
```bash
# Re-export models from training environment
python scripts/export_models.py

# Verify model integrity
python scripts/validate_models.py
```

**C. Memory Issues with Large Models**
```python
# Lazy load models (modify app/services/ml_service.py)
class MLService:
    _annual_model = None
    
    @property
    def annual_model(self):
        if self._annual_model is None:
            self._annual_model = self._load_annual_model()
        return self._annual_model
```

### 3. Database Connection Issues

**Symptoms:**
- "Connection refused" errors
- Timeouts on database queries
- Authentication failures

**Diagnosis:**
```bash
# Test connectivity from application container
telnet $DATABASE_HOST 5432

# Check RDS instance status
aws rds describe-db-instances --db-instance-identifier accunode-prod-db

# Verify connection parameters
echo "Host: $DATABASE_HOST"
echo "Database: $DATABASE_NAME"
echo "User: $DATABASE_USER"
```

**Solutions:**

**A. Security Group Issues**
```bash
# Check ECS security group allows outbound to RDS port
aws ec2 describe-security-groups --group-ids sg-ecs-12345 --query 'SecurityGroups[0].IpPermissionsEgress'

# Check RDS security group allows inbound from ECS
aws ec2 describe-security-groups --group-ids sg-rds-12345 --query 'SecurityGroups[0].IpPermissions'

# Fix: Add rule allowing ECS SG → RDS SG on port 5432
```

**B. Connection Pool Exhaustion**
```python
# Check connection pool settings in database.py
engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # Increase if needed
    max_overflow=10,      # Increase if needed
    pool_pre_ping=True,   # Enable connection validation
    pool_recycle=3600     # Recycle connections hourly
)
```

**C. Database Credentials Issues**
```bash
# Verify credentials in Parameter Store
aws ssm get-parameter --name "/accunode/production/database/password" --with-decryption

# Test manual connection
PGPASSWORD=actual_password psql -h host -U user -d database
```

### 4. Authentication and Authorization Issues

**Symptoms:**
- 401 Unauthorized errors
- JWT token validation failures
- Users can't access their own data

**Diagnosis:**
```bash
# Check JWT token structure
echo "JWT_TOKEN" | cut -d. -f2 | base64 -d | jq .

# Verify JWT secret
aws ssm get-parameter --name "/accunode/production/jwt/secret" --with-decryption

# Test token generation
curl -X POST https://api.accunode.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"password"}'
```

**Solutions:**

**A. JWT Secret Mismatch**
```bash
# Ensure all containers use same JWT secret
# Update Parameter Store value
aws ssm put-parameter \
  --name "/accunode/production/jwt/secret" \
  --value "NEW_SECURE_SECRET" \
  --type "SecureString" \
  --overwrite

# Restart ECS service to pick up new secret
aws ecs update-service --cluster accunode-production --service accunode-api-service --force-new-deployment
```

**B. Token Expiration Issues**
```python
# Check token expiration settings
JWT_EXPIRE_MINUTES = 1440  # 24 hours

# Add refresh token endpoint
@app.post("/api/v1/auth/refresh")
async def refresh_token(current_user: User = Depends(get_current_user)):
    return {"access_token": create_access_token(data={"sub": current_user.email})}
```

**C. Permission Hierarchy Issues**
```python
# Verify role hierarchy in auth logic
def check_permission(user: User, resource_owner_id: str, required_level: str):
    if user.role == "super_admin":
        return True
    if required_level == "personal" and user.id == resource_owner_id:
        return True
    # Add organization-level checks
```

## Performance Issues

### 1. Slow API Response Times

**Symptoms:**
- Response times > 2 seconds
- Timeouts on prediction endpoints
- High CPU/memory usage

**Diagnosis:**
```bash
# Monitor response times
curl -w "%{time_total}\n" -o /dev/null -s https://api.accunode.com/health

# Check ECS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=accunode-api-service \
  --start-time 2025-10-05T00:00:00Z \
  --end-time 2025-10-05T23:59:59Z \
  --period 300 \
  --statistics Average,Maximum

# Profile application performance
pip install py-spy
py-spy record -o profile.svg --pid $(pgrep -f "gunicorn.*main:app")
```

**Solutions:**

**A. Database Query Optimization**
```python
# Add database query logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Optimize queries with proper indexes
# Add indexes for frequently queried columns
CREATE INDEX idx_predictions_user_id ON annual_predictions(created_by);
CREATE INDEX idx_predictions_org_id ON annual_predictions(organization_id);

# Use query optimization
from sqlalchemy.orm import joinedload
predictions = session.query(Prediction).options(
    joinedload(Prediction.company)
).filter(Prediction.created_by == user_id).all()
```

**B. ML Model Performance**
```python
# Cache model predictions for identical inputs
from functools import lru_cache

@lru_cache(maxsize=1000)
def predict_cached(ratios_tuple, model_type):
    return predict_default_risk(dict(ratios_tuple), model_type)

# Use async model loading
import asyncio

async def async_predict(ratios, model_type):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, predict_default_risk, ratios, model_type)
```

**C. Application Scaling**
```bash
# Scale ECS service
aws ecs update-service \
  --cluster accunode-production \
  --service accunode-api-service \
  --desired-count 4

# Increase container resources
# Update task definition with higher CPU/memory
```

### 2. Memory Issues

**Symptoms:**
- Out of memory errors
- Container restarts
- Gradual memory increase over time

**Diagnosis:**
```bash
# Monitor memory usage
docker stats container-id

# Check ECS memory metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name MemoryUtilization \
  --dimensions Name=ServiceName,Value=accunode-api-service

# Profile memory usage
pip install memory-profiler
mprof run python app/main.py
mprof plot
```

**Solutions:**

**A. Memory Leak Detection**
```python
# Add memory monitoring
import psutil
import gc

@app.middleware("http")
async def memory_monitor(request, call_next):
    response = await call_next(request)
    memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
    if memory_mb > 800:  # Alert if > 800MB
        logger.warning(f"High memory usage: {memory_mb}MB")
        gc.collect()  # Force garbage collection
    return response
```

**B. Model Memory Optimization**
```python
# Unload models when not needed
class MLService:
    def unload_models(self):
        self._annual_model = None
        self._quarterly_model = None
        gc.collect()

# Use model compression
import joblib
joblib.dump(model, 'model.pkl', compress=3)
```

**C. Container Memory Limits**
```json
// Update ECS task definition
{
  "memory": 2048,  // Increase from 1024
  "memoryReservation": 1024
}
```

## Infrastructure Issues

### 1. Load Balancer Issues

**Symptoms:**
- 502/503 errors from ALB
- Health check failures
- Intermittent connectivity

**Diagnosis:**
```bash
# Check ALB target health
aws elbv2 describe-target-health --target-group-arn arn:aws:elasticloadbalancing:us-east-1:account:targetgroup/accunode-tg/id

# Check ALB access logs
aws s3 ls s3://accunode-alb-logs/ --recursive | tail -20
aws s3 cp s3://accunode-alb-logs/latest-log-file - | grep " 5"  # 5xx errors
```

**Solutions:**

**A. Health Check Configuration**
```bash
# Verify health check path
curl -H "Host: api.accunode.com" http://container-ip:8000/health

# Update health check settings
aws elbv2 modify-target-group \
  --target-group-arn TARGET-GROUP-ARN \
  --health-check-path /health \
  --health-check-interval-seconds 30 \
  --healthy-threshold-count 2 \
  --unhealthy-threshold-count 5
```

**B. Security Group Rules**
```bash
# Ensure ALB can reach ECS containers
aws ec2 authorize-security-group-egress \
  --group-id sg-alb-12345 \
  --protocol tcp \
  --port 8000 \
  --source-group sg-ecs-12345
```

### 2. Database Performance Issues

**Symptoms:**
- Slow query performance
- Connection timeouts
- High database CPU

**Solutions:**

**A. Database Monitoring**
```bash
# Check RDS performance insights
aws rds describe-db-instances --db-instance-identifier accunode-prod-db

# Monitor slow queries
# Enable slow query log in RDS parameter group
```

**B. Query Optimization**
```sql
-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation 
FROM pg_stats 
WHERE tablename IN ('annual_predictions', 'quarterly_predictions');

-- Add performance indexes
CREATE INDEX CONCURRENTLY idx_predictions_created_at ON annual_predictions(created_at);
CREATE INDEX CONCURRENTLY idx_predictions_company_symbol ON annual_predictions(company_symbol);
```

## Monitoring and Alerting

### 1. Application Monitoring

```bash
# Set up CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "AccuNode-HighErrorRate" \
  --alarm-description "High error rate detected" \
  --metric-name HTTPCode_Target_5XX_Count \
  --namespace AWS/ApplicationELB \
  --statistic Sum \
  --period 300 \
  --threshold 10 \
  --comparison-operator GreaterThanThreshold

# Monitor custom metrics
aws logs create-log-group --log-group-name /aws/accunode/application-metrics
```

### 2. Health Check Endpoints

```python
# Enhanced health check endpoint
@app.get("/health")
async def enhanced_health_check(db: Session = Depends(get_db)):
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Database connectivity
    try:
        db.execute(text("SELECT 1"))
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Redis connectivity  
    try:
        redis_client.ping()
        health_status["checks"]["redis"] = "healthy"
    except Exception as e:
        health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # ML Models
    try:
        ml_service.get_annual_model()
        health_status["checks"]["ml_models"] = "healthy"
    except Exception as e:
        health_status["checks"]["ml_models"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    return health_status
```

## Emergency Procedures

### 1. Service Outage Response

```bash
# 1. Check service status
aws ecs describe-services --cluster accunode-production --services accunode-api-service

# 2. Check recent deployments
aws ecs list-tasks --cluster accunode-production --service-name accunode-api-service

# 3. Rollback if needed (see rollback-procedures.md)
aws ecs update-service \
  --cluster accunode-production \
  --service accunode-api-service \
  --task-definition accunode-api-task:PREVIOUS_REVISION

# 4. Scale up if capacity issue
aws ecs update-service \
  --cluster accunode-production \
  --service accunode-api-service \
  --desired-count 6
```

### 2. Database Emergency Access

```bash
# Access via bastion host
ssh -i bastion-key.pem ec2-user@bastion.accunode.com

# Connect to RDS
psql -h accunode-prod-db.xxxxxxxxx.us-east-1.rds.amazonaws.com -U accunode_user -d accunode_prod

# Check database status
SELECT * FROM pg_stat_activity WHERE state = 'active';
SELECT * FROM pg_stat_database WHERE datname = 'accunode_prod';
```

## Getting Help

### 1. Log Collection

```bash
# Collect all relevant logs
aws logs tail /ecs/accunode-api --since 1h > app-logs.txt
aws s3 sync s3://accunode-alb-logs/latest/ ./alb-logs/
aws rds download-db-log-file-portion --db-instance-identifier accunode-prod-db --log-file-name error/postgresql.log.2025-10-05-12
```

### 2. System Information

```bash
# Gather system state
aws ecs describe-clusters --clusters accunode-production > cluster-state.json
aws ecs describe-services --cluster accunode-production --services accunode-api-service > service-state.json
aws elbv2 describe-target-health --target-group-arn TARGET-GROUP-ARN > target-health.json
```

### 3. Contact Information

For critical issues requiring immediate attention:
- **On-call Engineer**: Check internal contact list
- **AWS Support**: If infrastructure-related
- **Development Team**: For application bugs
- **Security Team**: For security incidents

---

*For specific troubleshooting scenarios, also refer to:*
- *[Performance Debugging](./performance-debugging.md)*
- *[Database Troubleshooting](./database-troubleshooting.md)*  
- *[AWS Infrastructure Issues](./aws-infrastructure-issues.md)*
