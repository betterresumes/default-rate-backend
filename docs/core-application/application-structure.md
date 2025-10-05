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

### Included API Routers:
1. `/api/v1/auth` - User authentication and registration
2. `/api/v1/companies` - Company CRUD operations (4 endpoints)
3. `/api/v1/predictions` - ML prediction endpoints
4. `/api/v1/users` - User profile management
5. `/api/v1/organizations` - Organization management
6. `/api/v1/tenants` - Tenant administration
7. `/api/v1/admin` - Admin utilities

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





## 🎯 **Architecture Overview**

AccuNode is a **multi-tenant ML-based Default Rate Prediction API** built with FastAPI, utilizing machine learning models to predict corporate default probabilities based on financial ratios.

### **System Architecture Diagram**
```
┌─────────────────────────────────────────────────────────────────┐
│                    CLIENT APPLICATIONS                          │
│                       Web Apps (next.js)
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS/REST API
┌─────────────────────▼───────────────────────────────────────────┐
│                  APPLICATION LAYER                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Rate Limit  │  │ Auth/JWT    │  │ CORS/Security│            │
│  │ Middleware  │  │ Middleware  │  │ Headers      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
│                                                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ Predictions │  │ Companies   │  │ Auth & User │            │
│  │ API         │  │ API         │  │ Management  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                   SERVICE LAYER                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │ML Prediction│  │Company      │  │Bulk Upload  │            │
│  │Service      │  │Service      │  │Service      │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    DATA LAYER                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │PostgreSQL   │  │Redis Cache  │  │ML Models    │            │
│  │Database     │  │& Sessions   │  │(.pkl files) │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### **AWS Infrastructure Architecture**
```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET                                │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTPS
┌─────────────────────▼───────────────────────────────────────────┐
│                  CLOUDFRONT CDN                                │
│                  (Optional Static Assets)                      │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│              APPLICATION LOAD BALANCER                         │
│                    (Multi-AZ)                                  │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                 ECS FARGATE CLUSTER                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   Service   │  │   Service   │  │   Service   │            │
│  │   Task 1    │  │   Task 2    │  │   Task N    │            │
│  │ (Auto-Scale)│  │ (Auto-Scale)│  │ (Auto-Scale)│            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│                    DATA SERVICES                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │    RDS      │  │ElastiCache  │  │ Parameter   │            │
│  │ PostgreSQL  │  │   Redis     │  │   Store     │            │
│  │ (Multi-AZ)  │  │ (Clustered) │  │  (Secrets)  │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 💻 **Technology Stack**

### **Backend & API**
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **API Framework** | FastAPI | 0.104+ | High-performance async REST API |
| **Python Runtime** | Python | 3.11+ | Application runtime environment |
| **ASGI Server** | Uvicorn | Latest | Production ASGI server |
| **Validation** | Pydantic | 2.0+ | Request/response data validation |

### **Database & Storage**
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Primary Database** | PostgreSQL | 15+ | ACID-compliant relational database |
| **Cache & Sessions** | Redis | 7+ | In-memory cache and session store |
| **ORM** | SQLAlchemy | 2.0+ | Database abstraction and relationships |
| **Migrations** | Alembic | Latest | Database schema versioning |

### **Machine Learning**
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **ML Framework** | Scikit-learn | 1.3+ | Logistic regression models |
| **Gradient Boosting** | LightGBM | 4.0+ | Advanced ensemble models |
| **Data Processing** | Pandas | 2.0+ | Data manipulation and analysis |
| **Model Serialization** | Pickle | Built-in | Model persistence |

### **Security & Auth**
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Authentication** | JWT | PyJWT 2.8+ | Stateless token-based auth |
| **Password Hashing** | bcrypt | 4.0+ | Secure password storage |
| **Rate Limiting** | slowapi | Latest | Request rate limiting |
| **CORS** | FastAPI-CORS | Latest | Cross-origin resource sharing |

### **Infrastructure & DevOps**
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Containerization** | Docker | 24+ | Application containerization |
| **Container Orchestration** | AWS ECS Fargate | Latest | Serverless container management |
| **Load Balancer** | AWS ALB | Latest | Traffic distribution |
| **CI/CD** | GitHub Actions | Latest | Automated deployment pipeline |

---

## 🧩 **System Components**

### **1. Application Layer Components**

#### **API Gateway & Middleware Stack**
```python
# Middleware execution order (top to bottom)
├── CORS Middleware              # Cross-origin requests
├── Security Headers Middleware  # Security HTTP headers  
├── Rate Limiting Middleware     # Request throttling
├── Authentication Middleware    # JWT token validation
├── Request Logging Middleware   # Audit trail
└── Error Handler Middleware     # Global exception handling
```

#### **API Route Organization**
```
/api/v1/
├── /auth/                      # Authentication endpoints
│   ├── POST /login            # User authentication
│   ├── POST /register         # User registration  
│   ├── POST /verify-email     # Email verification
│   └── POST /refresh-token    # Token refresh
├── /predictions/              # ML prediction endpoints
│   ├── GET /annual            # List annual predictions
│   ├── POST /annual           # Create annual prediction
│   ├── GET /quarterly         # List quarterly predictions
│   ├── POST /quarterly        # Create quarterly prediction
│   └── POST /bulk-upload      # Bulk prediction upload
├── /companies/                # Company management
│   ├── GET /                  # List companies
│   ├── GET /{id}             # Get company details
│   └── POST /                 # Create company
└── /users/                    # User management
    ├── GET /profile           # User profile
    ├── PUT /profile           # Update profile  
    └── GET /organizations     # User organizations
```

### **2. Service Layer Components**

#### **ML Prediction Service**
```python
class MLPredictionService:
    """Core ML inference service"""
    
    def __init__(self):
        self.annual_models = self._load_annual_models()
        self.quarterly_models = self._load_quarterly_models()
        self.scalers = self._load_feature_scalers()
    
    async def predict_annual(self, financial_data: dict) -> dict:
        """Annual default prediction using dual model ensemble"""
        
    async def predict_quarterly(self, financial_data: dict) -> dict:
        """Quarterly prediction using triple model ensemble"""
```

#### **Company Management Service**
```python
class CompanyService:
    """Company entity management"""
    
    async def create_or_get_company(self, company_data: dict, user: User) -> Company:
        """Create new company or return existing with access control"""
        
    async def get_companies_for_user(self, user: User, filters: dict) -> List[Company]:
        """Get companies based on user access level"""
```

#### **Bulk Upload Service**
```python
class BulkUploadService:
    """Async bulk operations processing"""
    
    async def process_csv_upload(self, file_data: bytes, user: User) -> str:
        """Queue bulk CSV processing job"""
        
    async def get_bulk_job_status(self, job_id: str, user: User) -> dict:
        """Check bulk processing job status"""
```

### **3. Data Layer Components**

#### **Database Models Hierarchy**
```python
# Base model with common fields
BaseModel
├── created_at: DateTime
├── updated_at: DateTime  
└── id: UUID (Primary Key)

# Core entities inheriting from BaseModel
├── User (Authentication & Authorization)
├── Organization (Multi-tenancy)  
├── Company (Business entities)
├── AnnualPrediction (ML predictions)
└── QuarterlyPrediction (ML predictions)
```

---
