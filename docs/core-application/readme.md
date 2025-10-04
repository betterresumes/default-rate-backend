# Core Application Documentation

Technical documentation for the AccuNode application architecture, systems, and core components.

## 📋 Documentation Overview

This section contains detailed technical documentation for developers, architects, and system administrators working with the AccuNode codebase.

## 📚 Available Documents

### System Design
- **[System Architecture](./system-architecture.md)** - Complete system design, technology stack, and architectural patterns
- **[Application Structure](./application-structure.md)** - FastAPI application organization and code structure

### Security & Authentication  
- **[Authentication System](./authentication-system.md)** - Multi-tenant authentication, JWT tokens, and role-based access control

### Data Management
- **[Database Design](./database-design.md)** - Complete database schema, relationships, and constraints
- **[Database Architecture](./database-architecture.md)** - Database implementation details and data flow

### Machine Learning
- **[ML Pipeline](./ml-pipeline.md)** - Machine learning model pipeline, training, and deployment workflow

## 🏗️ System Overview

AccuNode is a **multi-tenant SaaS platform** that provides ML-powered financial risk assessment through RESTful APIs.

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    AccuNode Core System                     │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  FastAPI Application Layer                                 │
│  ├── Authentication & Authorization                        │
│  ├── Rate Limiting & Security Middleware                   │
│  ├── API Endpoints (v1)                                   │
│  └── Request/Response Validation                           │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Business Logic Layer                                      │
│  ├── ML Prediction Services                               │
│  ├── Company Management Services                          │
│  ├── User Management Services                             │
│  └── Bulk Processing Services                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│  Data Layer                                               │
│  ├── PostgreSQL Database (Multi-tenant)                   │
│  ├── Redis Cache & Sessions                              │
│  └── ML Model Storage                                    │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

| Feature | Description | Documentation |
|---------|-------------|---------------|
| **Multi-tenant Architecture** | Organization-based data isolation | [Authentication System](./authentication-system.md) |
| **ML Predictions** | Annual and quarterly default risk models | [ML Pipeline](./ml-pipeline.md) |
| **Role-based Access Control** | 5-level permission hierarchy | [Authentication System](./authentication-system.md) |
| **Bulk Processing** | Async CSV/Excel processing with Celery | [System Architecture](./system-architecture.md) |
| **Rate Limiting** | API throttling and usage controls | [System Architecture](./system-architecture.md) |

## 🔧 Technology Stack

### Backend Framework
- **FastAPI 2.0.0** - High-performance web framework
- **Python 3.11+** - Programming language
- **Pydantic** - Data validation and serialization

### Database & Cache
- **PostgreSQL 15** - Primary database with multi-tenant schema
- **SQLAlchemy 2.0** - Database ORM with async support
- **Redis 7** - Session storage and caching

### Machine Learning
- **Scikit-learn** - Annual logistic regression models
- **LightGBM** - Quarterly ensemble models
- **Pandas** - Data processing and feature engineering

### Infrastructure
- **AWS ECS Fargate** - Container orchestration
- **AWS RDS** - Managed PostgreSQL database  
- **AWS ElastiCache** - Managed Redis cache
- **AWS Application Load Balancer** - Load balancing and SSL termination

## 🚀 Getting Started

### For New Developers
1. **[Application Structure](./application-structure.md)** - Understand the codebase organization
2. **[Database Architecture](./database-architecture.md)** - Learn the data model
3. **[Authentication System](./authentication-system.md)** - Understand security and permissions

### For System Architects
1. **[System Architecture](./system-architecture.md)** - Complete system design overview
2. **[Database Design](./database-design.md)** - Detailed database schema
3. **[ML Pipeline](./ml-pipeline.md)** - Machine learning workflow

### For DevOps Engineers
1. **[System Architecture](./system-architecture.md)** - Infrastructure requirements
2. **[Database Design](./database-design.md)** - Database deployment needs
3. **[Authentication System](./authentication-system.md)** - Security considerations

## 📊 Current System Metrics

| Component | Status | Version | Performance |
|-----------|--------|---------|-------------|
| **FastAPI App** | ✅ Production | v2.0.0 | <200ms response time |
| **Database** | ✅ Production | PostgreSQL 15 | <50ms query time |
| **ML Models** | ✅ Production | v1.0 | <100ms prediction time |
| **Cache** | ✅ Production | Redis 7 | <5ms response time |

## 🔗 Related Documentation

- **[API Documentation](../api-documentation/readme.md)** - Complete API reference and integration guides
- **[Infrastructure Documentation](../infrastructure/)** - AWS infrastructure setup and configuration
- **[Development Documentation](../development/)** - Development workflow and local setup
- **[Deployment Documentation](../deployment/)** - Production deployment guides

## 📞 Support

For technical questions about the core application:
1. Review the specific documentation sections above
2. Check the [Common Issues](../troubleshooting/common-issues.md) troubleshooting guide
3. Contact the development team for application-specific issues

---

*Last Updated: October 2025 | AccuNode Development Team*
