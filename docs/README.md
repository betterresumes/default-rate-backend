# AccuNode Documentation

Complete documentation for the AccuNode ML-powered default rate prediction API system.

## 📚 Documentation Structure

### 🏗️ [Core Application](./core-application/)
Essential technical documentation for the application architecture and systems.

- **[System Architecture](./core-application/system-architecture.md)** - Complete system design and architecture overview
- **[Authentication System](./core-application/authentication-system.md)** - Multi-tenant authentication and authorization
- **[Database Design](./core-application/database-design.md)** - Database schema and data architecture
- **[Database Architecture](./core-application/database-architecture.md)** - Database implementation details
- **[ML Pipeline](./core-application/ml-pipeline.md)** - Machine learning model pipeline and workflow  
- **[Application Structure](./core-application/application-structure.md)** - FastAPI application code organization
- **[Access Model & Ownership](./core-application/access-model.md)** - Roles, access levels (personal/org/system), and owner-only edits

### 🔌 [API Documentation](./api-documentation/)
Complete API reference and integration guides.

- **[API Overview](./api-documentation/api-overview.md)** - General API information and getting started
- **[Authentication API](./api-documentation/authentication-api.md)** - User registration, login, and token management
- **[Companies API](./api-documentation/companies-api.md)** - Company management and organization access
- **[Predictions API](./api-documentation/predictions-api.md)** - ML prediction endpoints and usage
- **[Users API](./api-documentation/users-api.md)** - User profile and management endpoints
- **[Organizations API](./api-documentation/organizations-api.md)** - Organization CRUD, whitelists, join tokens, global access
- **[Tenants API](./api-documentation/tenants-api.md)** - Tenant CRUD and statistics
- **[Scaling API](./api-documentation/scaling-api.md)** - Auto-scaling status, metrics, recommendations and controls
- **[Rate Limits](./api-documentation/rate-limits.md)** - Request throttling policies and limits
- **[Error Handling](./api-documentation/error-handling.md)** - Error formats and common responses
- **[Health Endpoint](./api-documentation/health-endpoints.md)** - System health and readiness

### ☁️ [Infrastructure](./infrastructure/)
AWS infrastructure setup and deployment documentation.

- **[ECS Fargate Setup](./infrastructure/ecs-fargate-setup.md)** - Container deployment on AWS Fargate
- **[Database Infrastructure](./infrastructure/database-infrastructure.md)** - AWS RDS PostgreSQL setup
- **[Load Balancer Setup](./infrastructure/load-balancer-setup.md)** - Application Load Balancer configuration
- **[Security Groups](./infrastructure/security-groups.md)** - Network security configuration

### 🚀 [Deployment](./deployment/)
Production deployment guides and CI/CD workflows.

- **[Production Deployment](./deployment/production-deployment.md)** - Complete production deployment guide
- **[CI/CD Pipeline](./deployment/cicd-pipeline.md)** - Current GitHub Actions pipeline
- **[Environment Configuration](./deployment/environment-configuration.md)** - Env vars and secrets
- **[Rollback Procedures](./deployment/rollback-procedures.md)** - Emergency rollback

### 💻 [Development](./development/)
Local development setup and developer workflows.

- **[Local Setup](./development/local-setup.md)** - Complete local development environment setup
- **[Development Workflow](./development/development-workflow.md)** - Git workflow and development practices

### 🛠️ [Troubleshooting](./troubleshooting/)
Common issues, debugging guides, and operational procedures.

- **[Common Issues](./troubleshooting/common-issues.md)** - Frequently encountered problems and solutions

---

## 🚀 Quick Start Guides

### For Developers
1. **[Local Setup](./development/local-setup.md)** - Set up your development environment
2. **[API Overview](./api-documentation/api-overview.md)** - Understand the API structure
3. **[Development Workflow](./development/development-workflow.md)** - Learn the development process

### For DevOps Engineers  
1. **[System Architecture](./core-application/system-architecture.md)** - Understand the system design
2. **[Infrastructure Setup](./infrastructure/ecs-fargate-setup.md)** - Deploy AWS infrastructure
3. **[Production Deployment](./deployment/production-deployment.md)** - Configure deployments

### For API Users
1. **[API Overview](./api-documentation/api-overview.md)** - Get started with the API
2. **[Authentication API](./api-documentation/authentication-api.md)** - Learn how to authenticate
3. **[Predictions API](./api-documentation/predictions-api.md)** - Start making predictions
4. **[Rate Limits](./api-documentation/rate-limits.md)** - Know your request budget
5. **[Error Handling](./api-documentation/error-handling.md)** - Understand responses

---

## 📊 System Overview

**AccuNode** is a multi-tenant SaaS platform that provides ML-powered financial risk assessment through RESTful APIs.

### Key Features
- **Multi-tenant Architecture** - Organization-based data isolation
- **ML Predictions** - Annual and quarterly default risk prediction models  
- **Role-based Access Control** - 5-level permission hierarchy
- **Bulk Processing** - Async CSV/Excel file processing with Celery
- **Rate Limiting** - API throttling and usage controls
- **AWS Native** - ECS Fargate, RDS, ElastiCache deployment

### Technology Stack
- **Backend**: FastAPI 2.0.0, Python 3.11+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **ML Models**: Scikit-learn, LightGBM ensemble models
- **Cache**: Redis for session management
- **Queue**: Celery with Redis broker
- **Infrastructure**: AWS ECS Fargate, RDS, ALB
- **CI/CD**: GitHub Actions

### Machine Learning Models
- **Annual Predictions**: 5 financial ratios (long_term_debt_to_total_capital, total_debt_to_ebitda, net_income_margin, ebit_to_interest_expense, return_on_assets)
- **Quarterly Predictions**: 4 financial ratios (total_debt_to_ebitda, sga_margin, long_term_debt_to_total_capital, return_on_capital)
- **Risk Assessment**: Multi-level risk classification with confidence scores
- **Bulk Processing**: Excel/CSV file upload with background job processing

---

## 📈 Current Status

| Component | Status | Version | Notes |
|-----------|--------|---------|--------|  
| **Core API** | ✅ Production Ready | v2.0.0 | FastAPI with full authentication |
| **ML Models** | ✅ Production Ready | v1.0 | Annual + Quarterly ensemble models |
| **Database** | ✅ Production Ready | PostgreSQL 15 | Multi-tenant schema |
| **Infrastructure** | ✅ Production Ready | AWS | ECS Fargate deployment |
| **Documentation** | ✅ Complete | v2.0 | Comprehensive guides |

---

## 🤝 Contributing

Please refer to the [Development Workflow](./development/development-workflow.md) for contribution guidelines and development practices.

## 📞 Support

For technical support or questions:
- Review [Troubleshooting Guide](./troubleshooting/common-issues.md)
- Check [API Documentation](./api-documentation/)
- Contact the development team

---

*Last Updated: October 2025 | AccuNode Team*
