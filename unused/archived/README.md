# Financial Default Risk Prediction API - Backend

A comprehensive enterprise-grade multi-tenant financial default risk prediction platform built with FastAPI, PostgreSQL, and Celery.

## 🏗️ **Project Structure**

```
backend/
├── app/                          # Main application package
│   ├── __init__.py              # Package initialization
│   ├── main.py                  # FastAPI application factory
│   │
│   ├── core/                    # Core functionality
│   │   ├── __init__.py
│   │   └── database.py         # Database models and connection
│   │
│   ├── api/                     # API routes
│   │   ├── __init__.py
│   │   └── v1/                 # API version 1
│   │       ├── __init__.py
│   │       ├── auth_multi_tenant.py      # Authentication & joining
│   │       ├── tenants.py               # Tenant management
│   │       ├── organizations_multi_tenant.py # Organization management
│   │       ├── users.py                 # User management
│   │       ├── companies.py             # Companies API
│   │       └── predictions.py           # Predictions API
│   │
│   ├── schemas/                 # Pydantic schemas
│   │   ├── __init__.py
│   │   └── schemas.py          # Request/response models
│   │
│   ├── services/                # Business logic layer
│   │   ├── __init__.py
│   │   ├── services.py         # Core business services
│   │   ├── email_service.py    # Email functionality
│   │   ├── ml_service.py       # ML prediction services
│   │   └── quarterly_ml_service.py # Quarterly ML services
│   │
│   ├── workers/                 # Background task processing
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── tasks.py            # Background tasks
│   │   └── workers.py          # Worker processes
│   │
│   ├── utils/                   # Utility functions
│   │   ├── __init__.py
│   │   ├── tenant_utils.py     # Tenant utilities
│   │   ├── join_link_manager.py # Join link management
│   │   └── org_code_manager.py  # Organization code management
│   │
│   └── models/                  # ML models and related files
│       ├── __init__.py
│       └── *.pkl               # Trained ML models
│
├── tests/                       # Test suite
│   └── (test files)
│
├── docs/                        # Documentation
│   └── (documentation files)
│
├── deployment/                  # Deployment configurations
│   ├── Dockerfile.local        # Local development Docker
│   ├── docker-compose.local.yml # Local Docker Compose
│   ├── requirements.local.txt   # Local requirements
│   ├── requirements.prod.txt    # Production requirements
│   ├── railway.toml            # Railway deployment
│   ├── railway-worker.toml     # Railway worker config
│   ├── nixpacks.toml           # Nixpacks config
│   └── deploy-*.sh             # Deployment scripts
│
├── storage/                     # Data storage
│   ├── bulk_upload_files/      # Bulk upload data
│   └── quarterly_upload_files/ # Quarterly data
│
├── archived/                    # Legacy code (ignored in new structure)
│
├── main.py                     # Application entry point
├── requirements.txt            # Main Python dependencies
├── Dockerfile                  # Production Docker image
├── docker-compose.prod.yml     # Production Docker Compose
├── .env                        # Environment variables
├── .env.example               # Environment template
└── README.md                  # This file
```

## 🚀 **Quick Start**

### **Development**
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your configuration

# Start development server
python main.py
```

### **Production**
```bash
# Using Docker
docker-compose -f docker-compose.prod.yml up -d

# Or direct deployment
ENV=production python main.py
```

## 📚 **API Documentation**

Once running, access the API documentation at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🏢 **Multi-Tenant Architecture**

### **Tenant Hierarchy**
```
Platform (Global)
├── Tenant (Enterprise)
│   ├── Organization A
│   │   ├── Users (Members)
│   │   └── Whitelist
│   └── Organization B
│       ├── Users (Members)
│       └── Whitelist
└── Tenant (Small Business)
    └── Organization
        ├── Users (Members)
        └── Whitelist
```

### **Role-Based Permissions**
- **Super Admin**: Platform management
- **Tenant Admin**: Tenant and organization management
- **Org Admin**: Organization and member management
- **Member**: Full organization access
- **User**: Basic organization access

## 🔌 **API Endpoints**

### **Authentication** (`/api/auth/`)
- `POST /register` - Register new user
- `POST /login` - User login
- `POST /join` - Join organization (whitelist-based)
- `GET /me` - Get user profile
- `POST /refresh` - Refresh JWT token
- `POST /logout` - Logout

### **Tenant Management** (`/api/tenants/`)
- `POST /` - Create tenant (Super Admin)
- `GET /` - List tenants (Super Admin)
- `PUT /{id}` - Update tenant
- `DELETE /{id}` - Delete tenant

### **Organization Management** (`/api/organizations/`)
- `POST /` - Create organization
- `GET /` - List organizations
- `PUT /{id}` - Update organization
- `DELETE /{id}` - Delete organization
- `POST /{id}/whitelist` - Manage whitelist
- `GET /{id}/whitelist` - View whitelist

### **User Management** (`/api/users/`)
- `GET /profile` - User profile
- `PUT /profile` - Update profile
- `GET /organization-members` - List members
- `PUT /members/{id}/role` - Change role
- `PUT /members/{id}/activate` - Activate/deactivate

### **Companies API** (`/api/v1/companies/`)
- Company data management for predictions

### **Predictions API** (`/api/v1/predictions/`)
- Annual and quarterly default risk predictions
- Background processing with Celery
- ML model integration

## 🔧 **Configuration**

### **Environment Variables**
```env
# Database
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Email
RESEND_API_KEY=your-resend-api-key

# Redis (for Celery)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# CORS
CORS_ORIGIN=http://localhost:3000

# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false
WORKERS=4
```

## 🏗️ **Architecture Benefits**

### **Clean Separation of Concerns**
- **`core/`**: Database and foundational components
- **`api/`**: HTTP interface and routing
- **`services/`**: Business logic and external integrations
- **`workers/`**: Background task processing
- **`utils/`**: Shared utilities and helpers

### **Scalability**
- Versioned APIs (`/api/v1/`, `/api/v2/`)
- Microservice-ready structure
- Horizontal scaling with workers
- Multi-tenant data isolation

### **Maintainability**
- Clear module boundaries
- Consistent import patterns
- Comprehensive documentation
- Type hints and validation

### **Enterprise Features**
- Multi-tenant architecture
- Role-based access control
- Whitelist-based security
- Background task processing
- ML model integration
- Comprehensive API documentation

## 🧪 **Testing**

```bash
# Run tests
pytest tests/

# With coverage
pytest tests/ --cov=app
```

## 📦 **Deployment**

See `deployment/` directory for:
- Docker configurations
- Railway deployment
- Environment-specific requirements
- Deployment scripts

## 🔒 **Security Features**

- JWT-based authentication
- Role-based access control
- Multi-tenant data isolation
- Whitelist-based organization joining
- Input validation with Pydantic
- CORS protection
- Environment-based configuration
