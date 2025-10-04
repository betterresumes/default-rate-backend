# 🔄 AccuNode Development Workflow Guide

## Overview

This document explains the complete development workflow for AccuNode, from local development in the `prod-dev` branch to production deployment via the `prod` branch.

---

## 🌳 Branch Strategy

### **Branch Structure**
```
main (legacy)
├── prod-dev (🚧 Active Development)
│   ├── Local Docker environment
│   ├── PostgreSQL + Redis containers
│   ├── Hot-reload development
│   └── Full testing suite
└── prod (🚀 Production Deployment)
    ├── AWS ECS Fargate deployment
    ├── RDS PostgreSQL + ElastiCache
    ├── Auto-scaling infrastructure
    └── Production monitoring
```

### **Branch Purposes**
- **`prod-dev`**: Local development with Docker
- **`prod`**: Production deployment (auto-deploys to AWS)

---

## 🚀 Complete Development Workflow

### **Step 1: Setup Local Environment**
```bash
# Clone and switch to development branch
git checkout prod-dev
git pull origin prod-dev

# Setup local Docker environment
make setup
# or
./scripts/local/dev-setup.sh

# Verify setup
make status
curl http://localhost:8000/health
```

### **Step 2: Daily Development**
```bash
# Start development environment
make start

# Make code changes (auto-reloads)
# Edit files in app/, tests/, etc.

# Test your changes
make test

# View logs
make logs
make logs-api

# Connect to database for debugging  
make db
```

### **Step 3: Testing & Validation**
```bash
# Run full test suite
make test

# Run specific tests
./scripts/local/dev-test.sh tests/test_auth.py

# Manual API testing
open http://localhost:8000/docs

# Database operations
make db
SELECT * FROM tenants LIMIT 5;
```

### **Step 4: Commit Changes**
```bash
# Commit to prod-dev branch
git add .
git commit -m "feat: add new prediction endpoint"
git push origin prod-dev
```

### **Step 5: Deploy to Production**
```bash
# Switch to production branch
git checkout prod

# Merge your tested changes
git merge prod-dev

# Deploy to AWS (triggers auto-deployment)
git push origin prod
```

### **Step 6: Monitor Deployment**
```bash
# Check GitHub Actions
# Visit: https://github.com/your-repo/actions

# Monitor AWS deployment
aws ecs describe-services --cluster AccuNode-Production \
  --services accunode-api-service accunode-worker-service

# Test production API
curl https://your-production-url.com/health
```

---

## 🛠️ Local Development Commands

### **Essential Commands**
```bash
# Setup & Management
make setup          # Initial setup
make start          # Start services  
make stop           # Stop services
make restart        # Restart services
make status         # Check status
make clean          # Clean environment

# Development
make logs           # All logs
make logs-api       # API logs only
make logs-db        # Database logs only
make db             # Connect to database
make shell          # Shell in API container

# Testing
make test           # Run all tests
make test-watch     # Tests in watch mode

# Building
make build          # Rebuild containers
```

### **Script Alternatives**
```bash
./scripts/local/dev-setup.sh     # Complete setup
./scripts/local/dev-logs.sh      # View logs
./scripts/local/dev-db.sh        # Database connection
./scripts/local/dev-test.sh      # Run tests
./scripts/local/dev-restart.sh   # Restart services
./scripts/local/dev-stop.sh      # Stop services
```

---

## 🌐 Environment Configurations

### **Local Development Environment (`prod-dev`)**
```yaml
# Services
- FastAPI API (localhost:8000)
- PostgreSQL (localhost:5432) 
- Redis (localhost:6379)
- Celery Worker
- LocalStack (AWS simulation)

# Configuration
- Database: accunode_development
- User: admin
- Password: dev_password_123
- Auto-reload: Enabled
- Debug mode: Enabled
```

### **Production Environment (`prod`)**
```yaml
# AWS Services
- ECS Fargate (auto-scaling)
- RDS PostgreSQL (private subnet)
- ElastiCache Redis
- Application Load Balancer
- Parameter Store (secrets)

# Security
- Private database access via bastion
- JWT authentication
- Rate limiting enabled
- Security headers configured
```

---

## 🗄️ Database Operations

### **Local Development Database**
```bash
# Quick connection
make db

# Manual connection
psql -h localhost -U admin -d accunode_development -p 5432
# Password: dev_password_123

# Common operations
\dt                           # List tables
\d organizations             # Describe table
SELECT COUNT(*) FROM tenants; # Query data
\q                           # Exit
```

### **Production Database Access**
```bash
# Connect via bastion host
./docs/aws/database/connect-database.sh

# Or manual connection (after setting up tunnel)
ssh -i bastion-access-key.pem -L 5432:db-endpoint:5432 ec2-user@bastion-ip
psql -h localhost -U admin -d accunode_production -p 5432
```

---

## 🧪 Testing Strategy

### **Local Testing Workflow**
```bash
# 1. Unit Tests
make test

# 2. Integration Tests  
./scripts/local/dev-test.sh tests/test_api/

# 3. Manual API Testing
open http://localhost:8000/docs

# 4. Database Testing
make db
# Run test queries

# 5. Load Testing (optional)
docker-compose -f docker-compose.dev.yml exec api pytest tests/load/
```

### **Test Types**
- **Unit Tests**: Function-level testing
- **Integration Tests**: API endpoint testing
- **Database Tests**: Model and query testing
- **Authentication Tests**: Security testing
- **Performance Tests**: Load and stress testing

---

## 🚀 Deployment Process

### **Automatic Deployment (Recommended)**
```bash
# 1. Develop and test in prod-dev
git checkout prod-dev
# Make changes, test thoroughly

# 2. Merge to prod and push
git checkout prod
git merge prod-dev
git push origin prod

# 3. GitHub Actions automatically:
# - Builds Docker image
# - Pushes to ECR  
# - Updates ECS service
# - Monitors deployment
```

### **Deployment Verification**
```bash
# Check GitHub Actions
# Visit repository → Actions tab

# Verify ECS deployment
aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service

# Test production endpoints
curl https://your-api.com/health
curl https://your-api.com/docs
```

### **Rollback if Needed**
```bash
# Automatic rollback on failure (configured in ECS)
# Manual rollback:
aws ecs update-service --cluster AccuNode-Production \
  --service accunode-api-service \
  --task-definition accunode-api:PREVIOUS_VERSION
```

---

## 🔍 Debugging & Troubleshooting

### **Local Development Issues**

#### **Services Won't Start**
```bash
# Check Docker
docker info

# Clean restart
make clean
make setup

# Check logs
make logs
```

#### **Database Connection Issues**
```bash
# Check PostgreSQL container
make logs-db

# Reset database
docker-compose -f docker-compose.dev.yml down -v
make setup
```

#### **API Not Responding**
```bash
# Check API logs
make logs-api

# Restart API service
make restart api

# Check if port is available
netstat -an | grep :8000
```

#### **Import Errors**
```bash
# Rebuild containers
make build

# Check Python path
make shell
python -c "import sys; print(sys.path)"
```

### **Production Issues**

#### **Deployment Failures**
1. Check GitHub Actions logs
2. Review ECS service events
3. Check CloudWatch logs
4. Verify ECR image push

#### **Application Errors**
1. Check CloudWatch application logs
2. Monitor ECS service metrics
3. Check database connectivity via bastion
4. Review Parameter Store configuration

#### **Performance Issues**  
1. Monitor CloudWatch metrics
2. Check ECS service scaling
3. Review database performance insights
4. Analyze Redis cache hit rates

---

## 📊 Monitoring & Observability

### **Local Development Monitoring**
```bash
# Service status
make status

# Real-time logs
make logs

# Resource usage
docker stats

# Database performance
make db
SELECT * FROM pg_stat_activity;
```

### **Production Monitoring**
- **CloudWatch**: Metrics, logs, and alarms
- **ECS Console**: Service health and scaling
- **RDS Console**: Database performance
- **Application Metrics**: Custom business metrics

---

## 🔒 Security Considerations

### **Development Security**
- Use development passwords (not production secrets)
- Enable debug mode for detailed error messages
- Relaxed rate limiting for testing
- Local-only database access

### **Production Security**
- Strong passwords and encrypted secrets
- Private database subnet with bastion access
- Strict rate limiting and security headers
- JWT authentication with proper key rotation

---

## 📈 Performance Optimization

### **Local Development**
```bash
# Optimize Docker
docker system prune -f

# Monitor container resources
docker stats

# Use efficient queries
make db
EXPLAIN ANALYZE SELECT * FROM organizations WHERE tenant_id = 'uuid';
```

### **Production Optimization**
- Auto-scaling policies (CPU-based)
- Connection pooling for database
- Redis caching for frequent queries
- Optimized SQL queries with proper indexing

---

## 🎯 Best Practices

### **Code Development**
1. **Always develop in `prod-dev` branch**
2. **Test thoroughly before merging to `prod`**
3. **Use meaningful commit messages**
4. **Write tests for new features**
5. **Follow code style guidelines**

### **Git Workflow**
```bash
# Good practice
git checkout prod-dev
git pull origin prod-dev
# Make changes
make test
git add .
git commit -m "feat: descriptive message"
git push origin prod-dev

# Deploy when ready
git checkout prod  
git merge prod-dev
git push origin prod
```

### **Testing Practice**
```bash
# Before every commit
make test

# Before production deployment  
make test
# Manual testing via /docs
# Database query testing
```

### **Documentation**
- Update documentation for new features
- Keep environment configs in sync
- Document any manual deployment steps
- Update troubleshooting guides

---

## 🆘 Emergency Procedures

### **Critical Production Issue**
1. **Immediate**: Check service status in AWS console
2. **Rollback**: Use ECS to rollback to previous task definition
3. **Investigate**: Check CloudWatch logs and metrics
4. **Communicate**: Notify team and stakeholders
5. **Fix**: Develop fix in `prod-dev`, test, then deploy

### **Database Issues**
1. **Check connectivity** via bastion host
2. **Review RDS metrics** in AWS console
3. **Check application logs** for database errors
4. **Scale database** if performance issue
5. **Restore from backup** if data corruption

### **Service Outage**
1. **Check ECS service health**
2. **Review load balancer health checks**
3. **Monitor auto-scaling events**
4. **Check GitHub Actions** for deployment issues
5. **Manual intervention** if auto-recovery fails

---

## 📞 Support & Resources

### **Documentation Links**
- **Local Setup**: `docs/LOCAL_DEVELOPMENT_GUIDE.md`
- **Team Onboarding**: `docs/team/TEAM_ONBOARDING_GUIDE.md`
- **AWS Infrastructure**: `docs/aws/infrastructure/COMPLETE_INFRASTRUCTURE_GUIDE.md`
- **Database Access**: `docs/aws/database/COMPLETE_DATABASE_ACCESS_GUIDE.md`

### **Quick Help Commands**
```bash
make help           # All available commands
make docs          # Documentation links
make status        # Current service status
```

### **Support Contacts**
- **Infrastructure Issues**: Pranit
- **Development Questions**: Team Lead
- **Emergency**: On-call rotation

---

## ✅ Development Checklist

### **Daily Development**
- [ ] `git checkout prod-dev && git pull`
- [ ] `make start` (if not already running)
- [ ] Make code changes
- [ ] `make test` before committing
- [ ] `git commit` with descriptive message
- [ ] `git push origin prod-dev`

### **Before Production Deployment**
- [ ] All tests pass (`make test`)
- [ ] Manual testing completed
- [ ] Database migrations tested
- [ ] Performance impact assessed
- [ ] Documentation updated
- [ ] Team notified of deployment

### **Post-Deployment**
- [ ] Verify GitHub Actions successful
- [ ] Check ECS service health
- [ ] Test production endpoints
- [ ] Monitor CloudWatch for errors
- [ ] Confirm application metrics

---

## 🎉 Success Metrics

### **Development Productivity**
- Setup time: < 5 minutes with `make setup`
- Test execution: < 30 seconds for unit tests
- Hot reload: < 2 seconds for code changes
- Database operations: < 1 second for queries

### **Deployment Reliability**
- Deployment success rate: > 99%
- Rollback time: < 2 minutes
- Zero-downtime deployments
- Automated health checks

### **System Performance**
- API response time: < 200ms (95th percentile)
- Database query time: < 100ms (average)
- Auto-scaling response: < 5 minutes
- Cache hit rate: > 90%

---

*AccuNode Development Workflow Guide v1.0 | Updated: Oct 4, 2025 | Branches: prod-dev (local) → prod (AWS)*
