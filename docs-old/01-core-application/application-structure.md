# Application Structure

This document describes the actual AccuNode application structure based on the FastAPI implementation.

## Directory Structure

```
app/
├── main.py                    # FastAPI application entry point
├── core/
│   ├── config.py             # Configuration with Parameter Store support  
│   └── database.py           # SQLAlchemy models and database connection
├── api/v1/                   # API version 1 endpoints
│   ├── auth_multi_tenant.py  # Authentication and user registration
│   ├── companies.py          # Company management (4 endpoints)
│   ├── predictions.py        # ML prediction endpoints
│   ├── users.py              # User profile and management
│   ├── organizations_multi_tenant.py # Organization management
│   ├── tenants.py            # Tenant administration
│   ├── auth_admin.py         # Admin authentication utilities
│   └── debug.py              # Debug endpoints
├── services/
│   ├── ml_service.py         # Annual ML prediction service
│   ├── quarterly_ml_service.py # Quarterly ML prediction service
│   ├── services.py           # CompanyService business logic
│   └── bulk_upload_service.py # Bulk processing services
├── schemas/
│   └── schemas.py            # Pydantic models (765 lines)
├── middleware/
│   ├── rate_limiting.py      # API rate limiting middleware
│   └── security_headers.py   # Security header middleware
├── models/                   # ML model files
│   ├── annual_logistic_model.pkl
│   ├── quarterly_logistic_model.pkl
│   ├── quarterly_lgb_model.pkl
│   ├── scoring_info.pkl
│   └── quarterly_scoring_info.pkl
├── utils/                    # Utility functions
│   ├── tenant_utils.py       # Multi-tenant utilities
│   └── org_code_manager.py   # Organization management
└── workers/                  # Background job processing
    ├── celery_app.py         # Celery configuration
    └── tasks.py              # Background tasks
```

## Main Application (main.py)

The FastAPI application entry point:

```python
app = FastAPI(
    title="Default Rate Backend API", 
    version="1.0.0",
    lifespan=lifespan_handler
)
```

### Features:
- Lifespan management for startup/shutdown hooks
- Health check endpoint at `/health`
- 9 API router registrations
- CORS and middleware configuration
- Exception handling

### Included API Routers:
1. `/api/v1/auth` - User authentication and registration
2. `/api/v1/companies` - Company CRUD operations (4 endpoints)
3. `/api/v1/predictions` - ML prediction endpoints
4. `/api/v1/users` - User profile management
5. `/api/v1/organizations` - Organization management
6. `/api/v1/tenants` - Tenant administration
7. `/api/v1/admin` - Admin utilities
8. `/api/v1/debug` - Debug endpoints
9. `/api/v1/scaling` - Auto-scaling endpoints

## Database Layer (core/database.py)

### SQLAlchemy Models (6 main entities):

1. **Tenant** - Top-level multi-tenant isolation
2. **Organization** - Mid-level organizational grouping  
3. **User** - User accounts with 5-role hierarchy
4. **Company** - Company data with symbol and sector
5. **AnnualPrediction** - Annual predictions (5 financial ratios)
6. **QuarterlyPrediction** - Quarterly predictions (4 financial ratios)

### Additional Models:
- **BulkUploadJob** - Background job tracking
- **OrganizationMemberWhitelist** - Access control

### Database Configuration:
```python
engine = create_engine(
    get_database_url(),
    pool_size=20,
    max_overflow=30, 
    pool_pre_ping=True,
    pool_recycle=300
)
```

## Service Layer

### ML Services:

**Annual Predictions (services/ml_service.py)**
- Model: `annual_logistic_model.pkl`
- Input: 5 financial ratios
- Output: Probability, risk level, confidence

**Quarterly Predictions (services/quarterly_ml_service.py)**  
- Models: Logistic + LightGBM ensemble
- Input: 4 financial ratios
- Output: Multiple probabilities, ensemble result

**Business Logic (services/services.py)**
- `CompanyService` class with CRUD operations
- Pagination and filtering support
- Organization-based access control

## Configuration (core/config.py)

### Environment Support:
- **Development**: Local development setup
- **Production**: AWS deployment with Parameter Store
- **Testing**: Automated testing configuration

### AWS Integration:
- Parameter Store for secrets management
- Environment variable fallbacks
- Regional configuration support

### Key Settings:
```python
DATABASE_URL = get_parameter_store_value("/accunode/database-url")
REDIS_URL = get_parameter_store_value("/accunode/redis-url") 
SECRET_KEY = get_parameter_store_value("/accunode/secrets/secret-key")
```

## API Structure

### Company Endpoints (api/v1/companies.py):
1. `GET /` - List companies with pagination
2. `GET /{id}` - Get company by ID
3. `POST /` - Create new company  
4. `GET /search/{symbol}` - Search by symbol

### Authentication (api/v1/auth_multi_tenant.py):
- User registration (public endpoint)
- Login with JWT tokens
- Password change functionality
- Organization join functionality

### Predictions (api/v1/predictions.py):
- Annual prediction creation
- Quarterly prediction creation
- Bulk file upload processing
- Prediction history retrieval

## Middleware

### Rate Limiting (middleware/rate_limiting.py):
- `@rate_limit_ml` - ML operations (strict limits)
- `@rate_limit_auth` - Authentication endpoints
- `@rate_limit_upload` - File upload operations
- `@rate_limit_api` - General API operations

### Security (middleware/security_headers.py):
- Security header injection
- Request/response protection

## Background Workers (workers/)

### Celery Configuration:
- Redis-based message broker
- Task result storage
- Job status tracking
- Error handling and retries

### Background Tasks:
- Bulk Excel/CSV processing
- ML prediction batching
- Data validation and cleanup

This structure provides a scalable, maintainable foundation for the AccuNode default prediction system with clear separation of concerns.
