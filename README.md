# AccuNode Backend

**Multi-tenant ML-powered default rate prediction API system built with FastAPI.**

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Git

### Local Development Setup

1. **Clone and setup**
   ```bash
   git clone https://github.com/accunodeai/server.git
   cd backend
   make setup
   ```

2. **Start services**
   ```bash
   make start
   ```

3. **Access the application**
   - API: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

### Quick Commands

```bash
make help      # Show all available commands
make start     # Start development services
make stop      # Stop all services
make restart   # Restart services
make logs      # View service logs
make test      # Run tests
```

## 🏗️ Architecture

**Multi-tenant SaaS platform** with hierarchical organization structure:
- **Tenants** → **Organizations** → **Users**
- **Role-based access control**: `user`, `org_member`, `org_admin`, `tenant_admin`, `super_admin`
- **ML Models**: Annual (5 ratios) + Quarterly (4 ratios) predictions

### Tech Stack
- **API**: FastAPI 2.0 with async PostgreSQL
- **Database**: PostgreSQL + SQLAlchemy ORM
- **Cache**: Redis (ElastiCache in production)
- **ML**: scikit-learn, LightGBM, pandas
- **Infrastructure**: AWS ECS Fargate, RDS, ALB
- **CI/CD**: GitHub Actions → ECR → ECS

## 📊 ML Prediction Models

### Annual Model (5 Financial Ratios)
- **Input**: Current assets, Total assets, Current liabilities, Total liabilities, Earnings
- **Output**: Default probability prediction
- **Algorithm**: Logistic Regression with preprocessing pipeline

### Quarterly Model (4 Financial Ratios)
- **Input**: Current assets, Total assets, Working capital, Total debt
- **Output**: Default probability prediction  
- **Algorithm**: Ensemble (LightGBM + Logistic Regression)

## 🔐 Authentication & Access

### Role Hierarchy
```
super_admin     → Full system access
tenant_admin    → Tenant-wide management
org_admin       → Organization management
org_member      → Organization data access
user           → Personal data only
```

### Access Levels
- **Personal**: Own data only
- **Organization**: Organization-scoped data
- **System**: Cross-tenant access (super_admin)

## 🛠️ Development

### Environment Files
```bash
# Development
cp .env.example .env.development

# Required variables
DATABASE_URL=postgresql://admin:dev_password_123@localhost:5432/accunode_development
REDIS_URL=redis://:dev_redis_password@localhost:6379/0
SECRET_KEY=your-secret-key
```

```


## 🚢 Deployment

### Production (AWS ECS)
- **Trigger**: Push to `prod` branch
- **Pipeline**: GitHub Actions → ECR → ECS Fargate
- **Services**: API + Worker containers
- **Infrastructure**: RDS PostgreSQL + ElastiCache Redis

### Environment Configuration
```bash
# Production secrets via AWS Parameter Store
/accunode/prod/database-url
/accunode/prod/redis-url
/accunode/prod/secret-key
```

## 📚 Documentation

### Core Documentation
- **[Complete Docs](./docs/README.md)** - Full documentation index
- **[API Reference](./docs/api-documentation/)** - All API endpoints
- **[System Architecture](./docs/core-application/system-architecture.md)** - Technical design
- **[Database Design](./docs/core-application/database-design.md)** - Schema and relationships

