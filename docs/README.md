# AccuNode Documentation

Welcome to the AccuNode documentation - a FastAPI-based default probability prediction system with multi-tenant architecture and machine learning capabilities.

## Documentation Structure

### 01. Core Application
- [Main Application](01-core-application/README.md) - Application structure and core components
- [Database Architecture](01-core-application/database-architecture.md) - Database models and relationships
- [Authentication System](01-core-application/authentication.md) - JWT authentication with role hierarchy
- [Multi-Tenant Architecture](01-core-application/multi-tenant-architecture.md) - Tenant and organization management

### 02. API Documentation
- [API Overview](02-api-documentation/README.md) - Complete API reference
- [Authentication Endpoints](02-api-documentation/auth-endpoints.md) - User authentication APIs
- [Company Management](02-api-documentation/company-endpoints.md) - Company CRUD operations
- [Predictions API](02-api-documentation/prediction-endpoints.md) - ML prediction endpoints
- [User Management](02-api-documentation/user-endpoints.md) - User management APIs

### 03. AWS Infrastructure
- [Infrastructure Overview](03-aws-infrastructure/README.md) - AWS deployment architecture

### 04. Local Development
- [Development Setup](04-local-development/development-setup.md) - Local environment setup

## System Overview

AccuNode is a default rate prediction system built with:

- **Backend Framework**: FastAPI 2.0.0 with Python 3.9+
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache/Sessions**: Redis for rate limiting and session management  
- **ML Models**: Annual (5 ratios) and quarterly (4 ratios) prediction models
- **Authentication**: JWT-based with 5-role hierarchy
- **Architecture**: Multi-tenant with organization-based data isolation
- **Background Jobs**: Celery workers for bulk processing
- **Infrastructure**: Docker containerized with AWS deployment support

## Core Features

### Multi-Tenant Architecture
- **5-Role Hierarchy**: user → org_member → org_admin → tenant_admin → super_admin
- **Data Isolation**: Personal, organization, and system-level access
- **Organization Management**: Join tokens, whitelisting, role-based permissions

### Machine Learning
- **Annual Predictions**: 5-ratio logistic regression model (long-term debt/total capital, total debt/EBITDA, net income margin, EBIT/interest expense, return on assets)
- **Quarterly Predictions**: 4-ratio ensemble model (total debt/EBITDA, SG&A margin, long-term debt/total capital, return on capital)
- **Risk Assessment**: 4-level risk classification (LOW, MEDIUM, HIGH, CRITICAL)
- **Bulk Processing**: Excel/CSV file upload with background job processing

### API Features  
- **Company Management**: CRUD operations with symbol search
- **Prediction Management**: Create, retrieve, and analyze predictions
- **User Management**: Registration, profile management, role updates
- **Rate Limiting**: API protection with different limits per endpoint type
- **Health Checks**: Comprehensive system health monitoring

## Quick Start

1. **Local Development**: Follow [Development Setup](04-local-development/development-setup.md)
2. **API Reference**: See [API Documentation](02-api-documentation/README.md)
3. **Database Schema**: Review [Database Architecture](01-core-application/database-architecture.md)
