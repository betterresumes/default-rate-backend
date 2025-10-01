# AccuNode - Multi-tenant Financial Risk Assessment Platform

![AccuNode Logo](https://via.placeholder.com/400x100/2563eb/ffffff?text=AccuNode+API)

**AccuNode** is a production-ready, multi-tenant financial risk assessment platform built with FastAPI, providing ML-powered default predictions for financial institutions.

## 🚀 **Quick Start**

### Local Development
```bash
# Install dependencies
pip install -r requirements.dev.txt

# Set up environment
cp .env.example .env

# Start the application
python main.py
```

### AWS Production Deployment
```bash
# Configure AWS CLI
aws configure

# Run deployment scripts
cd deployment/aws/
chmod +x *.sh
./01-infrastructure.sh
./02-security-groups.sh
# ... follow deployment guide
```

## 📋 **Features**

### 🏢 **Multi-tenant Architecture**
- Complete tenant isolation
- Organization-level access control  
- 5-tier role system (Super Admin → Viewer)
- JWT-based authentication

### 🤖 **ML-Powered Predictions**
- Annual & quarterly default predictions
- LightGBM and Logistic Regression models
- Real-time scoring API
- Bulk prediction processing

### 📊 **Enterprise Features**
- Auto-scaling infrastructure
- Health monitoring & alerting
- Audit logging & compliance
- High-performance caching (Redis)

### 🔒 **Security & Compliance**
- VPC network isolation
- Encrypted data at rest & in transit
- AWS Parameter Store for secrets
- Multi-factor authentication ready

## 🏗️ **Architecture**

### **Technology Stack**
- **API Framework**: FastAPI + Uvicorn/Gunicorn
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis (ElastiCache)
- **Background Jobs**: Celery workers
- **ML Models**: Scikit-learn, LightGBM, Joblib
- **Containerization**: Docker + AWS ECR

### **AWS Services**
- **Compute**: EC2 with Auto Scaling Groups
- **Database**: RDS PostgreSQL  
- **Cache**: ElastiCache Redis
- **Load Balancer**: Application Load Balancer (ALB)
- **Networking**: VPC with public/private subnets
- **Secrets**: AWS Systems Manager Parameter Store
- **Monitoring**: CloudWatch

## 💰 **Cost Optimization**

### **Scaling Levels**

| Level | Users | Monthly Cost | Components |
|-------|--------|-------------|------------|
| **Startup** | 500-1K | $119/month | 2 API + 2 Workers (t3.small) |
| **Growth** | 1K-1.5K | $204/month | 3 API + 4 Workers (t3.small) |
| **Scale** | 1.5K+ | $300/month | 4 API + 6 Workers (t3.small) |

### **Auto-scaling Features**
- CPU-based scaling (50-70% thresholds)
- Queue-length based worker scaling
- Automatic cost optimization during low usage
- Reserved instance support for 30-50% savings

## 🛠️ **AWS Deployment Guide**

### **Prerequisites**
```bash
# Required AWS services access
✅ EC2, RDS, ElastiCache, VPC, IAM
✅ Systems Manager Parameter Store  
✅ CloudWatch, ALB, Auto Scaling
✅ ECR (Container Registry)
```

### **Phase 1: Infrastructure (30 min)**
```bash
cd deployment/aws/
./01-infrastructure.sh    # VPC, subnets, networking
./02-security-groups.sh   # Security groups & firewall
./03-parameter-store.sh   # Secrets management
```

### **Phase 2: Database & Cache (25 min)**  
```bash
./04-rds-setup.sh         # PostgreSQL RDS
./05-redis-setup.sh       # ElastiCache Redis
./06-test-connectivity.sh # Validate connections
```

### **Phase 3: Application (45 min)**
```bash
./07-build-image.sh       # Docker build & ECR push
./08-api-servers.sh       # API Auto Scaling Group  
./09-worker-nodes.sh      # Worker Auto Scaling Group
./10-load-balancer.sh     # ALB configuration
```

### **Phase 4: Production Setup (30 min)**
```bash
./11-ssl-setup.sh         # SSL certificates
./12-auto-scaling.sh      # Scaling policies
./13-monitoring.sh        # CloudWatch setup
./14-health-checks.sh     # Health validation
```

## 🔧 **Configuration**

### **Environment Variables**
```bash
# Core Application
ENVIRONMENT=production
PORT=8000
WORKERS=4

# AWS Configuration  
AWS_REGION=us-east-1
S3_BUCKET=accunode-ml-models

# Database (RDS PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/db

# Cache (ElastiCache Redis)
REDIS_URL=redis://host:6379/0

# Security (AWS Parameter Store)
SECRET_KEY=/accunode/secrets/secret_key
JWT_SECRET=/accunode/secrets/jwt_secret
```

### **Parameter Store Secrets**
```bash
# Required AWS Parameter Store values
/accunode/database/url           # PostgreSQL connection string
/accunode/redis/url             # Redis connection string  
/accunode/secrets/secret_key    # Application secret key
/accunode/secrets/jwt_secret    # JWT signing secret
/accunode/celery/broker_url     # Celery broker URL
```

## 📊 **API Endpoints**

### **Health & Status**
```
GET  /health                    # Comprehensive health check
GET  /                         # API information
```

### **Authentication**
```
POST /auth/register            # User registration
POST /auth/login              # User login  
POST /auth/refresh            # Token refresh
GET  /auth/me                 # Current user info
```

### **Multi-tenant Management**
```
GET  /tenants                 # List tenants
POST /tenants                 # Create tenant
GET  /organizations           # List organizations
POST /organizations           # Create organization
```

### **ML Predictions**
```
POST /predictions/annual      # Annual default prediction
POST /predictions/quarterly   # Quarterly default prediction
POST /predictions/bulk        # Bulk predictions
GET  /predictions/{id}        # Get prediction result
```

### **Admin & Management**
```
GET  /users                   # User management
GET  /companies               # Company data
GET  /scaling/status          # Auto-scaling status
POST /upload/bulk             # Bulk data upload
```

## 🔍 **Monitoring & Health Checks**

### **Health Check Response**
```json
{
  "status": "healthy",
  "timestamp": "2025-01-01T00:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": {"status": "healthy", "response_time": "15ms"},
    "redis": {"status": "healthy", "response_time": "5ms"},
    "ml_models": {"status": "healthy", "models_loaded": 4},
    "celery_workers": {"status": "healthy", "active_workers": 4}
  },
  "system": {
    "cpu_usage": "45%",
    "memory_usage": "60%",
    "disk_usage": "30%"
  }
}
```

### **CloudWatch Metrics**
- API response times (<200ms target)
- Error rates (<1% target)  
- CPU utilization (50-70% optimal)
- Queue processing rates
- Database connection pools
- Cost tracking per service

## 🚨 **Alerts & Thresholds**

### **Critical Alerts**
- API response time >500ms avg (5 min)
- Error rate >5% (2 min)
- CPU usage >80% (5 min)
- Database connections >80% (3 min)
- Queue backlog >100 tasks (5 min)

### **Cost Alerts**
- Daily spend increase >20%
- Monthly projection >budget
- Unused resources detected

## 🔒 **Security Features**

### **Network Security**
- VPC with private subnets for database/cache
- Security groups with minimal required access
- ALB with SSL/TLS termination
- No direct internet access to internal services

### **Application Security**
- JWT token authentication with expiration
- Multi-tenant data isolation
- Role-based access control (RBAC)
- Input validation & sanitization
- SQL injection prevention via ORM

### **Data Security**
- Encryption at rest (RDS, EBS volumes)
- Encryption in transit (SSL/TLS)
- Secrets management via AWS Parameter Store
- Audit logging for all data access
- Regular automated backups

## 📈 **Performance Optimization**

### **Database Optimization**
- Connection pooling with SQLAlchemy
- Query optimization with indexes
- Read replica support (optional)
- Automated backup retention

### **Caching Strategy**  
- Redis for session management
- API response caching
- ML model result caching
- Query result caching

### **Auto-scaling Configuration**
```yaml
API Servers:
  Min: 2, Max: 4
  Scale Up: CPU >70% (2 min)
  Scale Down: CPU <50% (5 min)

Workers:  
  Min: 2, Max: 6
  Scale Up: Queue >50 tasks (3 min)
  Scale Down: Queue <10 tasks (10 min)
```

## 🛡️ **Disaster Recovery**

### **Backup Strategy**
- Automated daily RDS snapshots (7-day retention)
- Cross-region backup replication (optional)
- Point-in-time recovery capability
- ML model versioning in S3

### **High Availability**
- Multi-AZ RDS deployment (optional, +$25/month)
- Auto Scaling Groups across multiple AZs
- Application Load Balancer health checks
- Automatic failure detection and recovery

## 📚 **Development**

### **Local Setup**
```bash
# Clone repository
git clone https://github.com/yourusername/accunode-backend.git
cd accunode-backend

# Install dependencies
pip install -r requirements.dev.txt

# Set up environment
cp .env.example .env
# Edit .env with your local configuration

# Start PostgreSQL and Redis (Docker)
docker-compose up -d postgres redis

# Run database migrations
python -c "from app.core.database import create_tables; create_tables()"

# Start the application
python main.py
```

### **Testing**
```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=app tests/

# Load testing
locust -f tests/load_test.py
```

### **Docker Development**
```bash
# Build image
docker build -t accunode-api .

# Run container
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql://..." \
  -e REDIS_URL="redis://..." \
  accunode-api
```

## 🤝 **Contributing**

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 **Support**

- **Documentation**: [Full API Docs](https://api.yourdomain.com/docs)
- **Issues**: [GitHub Issues](https://github.com/yourusername/accunode-backend/issues)
- **Email**: support@yourdomain.com

## 🎯 **Roadmap**

### **Q1 2025**
- [ ] GraphQL API support
- [ ] Advanced ML model A/B testing
- [ ] Real-time notifications system
- [ ] Mobile app API optimization

### **Q2 2025**  
- [ ] Multi-region deployment support
- [ ] Advanced analytics dashboard
- [ ] Machine learning model retraining pipeline
- [ ] Integration with external risk data providers

---

**Built with ❤️ for the financial services industry**

![AWS Architecture](https://via.placeholder.com/600x300/232f3e/ffffff?text=AccuNode+AWS+Architecture)

*AccuNode - Empowering financial institutions with intelligent risk assessment.*