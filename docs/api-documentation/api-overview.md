# API Overview

Complete API reference for AccuNode's Default Probability Prediction system based on the actual FastAPI implementation.

## System Overview

AccuNode provides a REST API built with FastAPI 2.0.0 with the following capabilities:

- **Application Title**: "Default Rate Backend API"
- **Version**: "1.0.0"  
- **Base URL**: `/api/v1`
- **Health Check**: `/health`
- **Authentication**: JWT-based with 5-role hierarchy
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Background Jobs**: Celery with Redis
- **ML Models**: Annual (5 ratios) and quarterly (4 ratios) predictions

## API Endpoints Structure

Based on the actual FastAPI router configuration in `app/main.py`, the API includes:

### Core API Routers
1. **Authentication** (`/api/v1/auth`) - User auth and registration
2. **Companies** (`/api/v1/companies`) - Company CRUD operations (4 endpoints)
3. **Predictions** (`/api/v1/predictions`) - ML prediction endpoints
4. **Users** (`/api/v1/users`) - User profile management
5. **Organizations** (`/api/v1/organizations`) - Organization management
6. **Tenants** (`/api/v1/tenants`) - Tenant administration
7. **Admin** (`/api/v1/admin`) - Administrative utilities
8. **Debug** (`/api/v1/debug`) - Debug endpoints
9. **Scaling** (`/api/v1/scaling`) - Auto-scaling endpoints

## Authentication System

### JWT Configuration
- **Algorithm**: HS256
- **Token Expiration**: 60 minutes (configurable)
- **Password Hashing**: Bcrypt with 5 rounds
- **Rate Limiting**: Applied to auth endpoints

### 5-Role Hierarchy
```
super_admin (4) ─── System-wide access
    ↓
tenant_admin (3) ── Tenant management  
    ↓
org_admin (2) ───── Organization management
    ↓
org_member (1) ──── Organization member
    ↓
user (0) ────────── Basic user (personal data only)
```

### Key Authentication Endpoints
- `POST /auth/register` - Public user registration (creates "user" role only)
- `POST /auth/login` - User login with JWT token response
- `POST /auth/change-password` - Password change (authenticated)
- `POST /auth/join-organization` - Join organization via token

## Company Management API

Based on `app/api/v1/companies.py`, the company API provides **4 endpoints**:

### 1. List Companies
```http
GET /api/v1/companies/
```
- **Pagination**: `?page=1&limit=10`
- **Filtering**: `?sector=Technology`
- **Search**: `?search=Apple`
- **Organization-based access control**
- **Returns**: Companies with prediction counts and relationships

### 2. Get Company by ID
```http
GET /api/v1/companies/{company_id}
```
- **Returns**: Full company details with annual/quarterly predictions
- **Access Control**: Filters data based on user's organization

### 3. Create Company
```http
POST /api/v1/companies/
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "market_cap": 2800000000000,
  "sector": "Technology"
}
```
- **Access Levels**: personal, organization, or system based on user role
- **Validation**: Symbol uniqueness within organization scope

### 4. Search by Symbol
```http
GET /api/v1/companies/search/{symbol}
```
- **Returns**: Company matching symbol
- **Case-insensitive search**
- **Organization filtering applied**

## Machine Learning Predictions

### Annual Predictions
**Endpoint**: `POST /api/v1/predictions/annual`

**Required Financial Ratios (5)**:
```json
{
  "company_symbol": "AAPL",
  "company_name": "Apple Inc.",
  "market_cap": 2800000,
  "sector": "Technology",
  "reporting_year": "2024",
  "long_term_debt_to_total_capital": 15.5,
  "total_debt_to_ebitda": 2.1,
  "net_income_margin": 25.3,
  "ebit_to_interest_expense": 45.2,
  "return_on_assets": 18.7
}
```

**ML Model**: 
- Logistic regression (`annual_logistic_model.pkl`)
- Binned scoring approach with `scoring_info.pkl`
- Risk classification: LOW (<2%), MEDIUM (2-5%), HIGH (5-15%), CRITICAL (>15%)

### Quarterly Predictions  
**Endpoint**: `POST /api/v1/predictions/quarterly`

**Required Financial Ratios (4)**:
```json
{
  "company_symbol": "AAPL",
  "company_name": "Apple Inc.",
  "market_cap": 2800000,
  "sector": "Technology", 
  "reporting_year": "2024",
  "reporting_quarter": "Q3",
  "total_debt_to_ebitda": 2.1,
  "sga_margin": 8.5,
  "long_term_debt_to_total_capital": 15.5,
  "return_on_capital": 22.3
}
```

**ML Models**:
- Ensemble approach: Logistic + LightGBM
- Models: `quarterly_logistic_model.pkl`, `quarterly_lgb_model.pkl`
- Returns: logistic_probability, gbm_probability, ensemble_probability

## User Management

### Profile Endpoints
- `GET /users/profile` - Basic user profile
- `PUT /users/profile` - Update profile (username, full_name)
- `GET /users/me` - Comprehensive profile with role-specific data

### Role-Specific Data Access
The `/users/me` endpoint returns different data based on user role:
- **super_admin**: All tenants and organizations
- **tenant_admin**: Tenant-specific data with organizations
- **org_admin/org_member**: Organization-specific data
- **user**: Personal profile only

## Multi-Tenant Architecture

### Access Control Levels
1. **Personal** (`access_level="personal"`)
   - Data owned by individual users
   - Only creator can access

2. **Organization** (`access_level="organization"`)
   - Shared within organization
   - Role-based access control

3. **System** (`access_level="system"`)
   - Global data for super administrators

### Organization Features
- Join tokens for user invitation
- Email whitelisting support
- Role-based permissions
- Data isolation between organizations

## Background Jobs & Bulk Processing

### Celery Worker Configuration
- **Broker/Backend**: Redis
- **Task Queue**: Bulk prediction processing
- **Job Tracking**: Status, progress, error handling
- **Files**: Celery configuration in `app/workers/celery_app.py`

### Bulk Upload Features
- Excel/CSV file processing
- Background job execution
- Progress tracking
- Error reporting and validation

## Database Models

### Core Entities (6 main models)
1. **Tenant** - Top-level multi-tenant isolation
2. **Organization** - Mid-level grouping within tenants
3. **User** - User accounts with role hierarchy
4. **Company** - Company information with access control
5. **AnnualPrediction** - Annual predictions with 5 ratios
6. **QuarterlyPrediction** - Quarterly predictions with 4 ratios

### Additional Models
- **BulkUploadJob** - Background job tracking
- **OrganizationMemberWhitelist** - Access control lists

## Rate Limiting

The API implements endpoint-specific rate limiting:

```python
@rate_limit_ml          # ML prediction endpoints (strict)
@rate_limit_auth        # Authentication endpoints
@rate_limit_upload      # File upload operations  
@rate_limit_api         # General API operations
```

## Health Check & Monitoring

### Health Check Endpoint
```http
GET /health
```
**Returns**: Comprehensive system status including:
- Database connectivity
- Redis connectivity
- ML model availability  
- System resource status

## Error Handling

### Standard Error Response Format
```json
{
  "success": false,
  "error": "error_type",
  "message": "Human-readable error message", 
  "detail": "Detailed error information"
}
```

### HTTP Status Codes
- **200**: Success
- **201**: Created
- **400**: Bad Request (validation errors)
- **401**: Unauthorized (authentication required)
- **403**: Forbidden (insufficient permissions)
- **404**: Not Found
- **422**: Unprocessable Entity
- **429**: Rate Limited
- **500**: Internal Server Error

## Configuration & Deployment

### Environment Configuration
- **Development**: Local development setup
- **Production**: AWS deployment with Parameter Store
- **Database**: PostgreSQL connection with pooling
- **Redis**: Session storage and task queue
- **Secret Management**: AWS Parameter Store integration

This API provides a robust, scalable system for default probability prediction with comprehensive multi-tenant support and advanced machine learning capabilities.
