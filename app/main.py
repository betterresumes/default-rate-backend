"""
Main FastAPI application factory and configuration.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import os
import logging
import time
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.core.database import create_tables
from app.api.v1.auth_multi_tenant import router as auth_router
from app.api.v1.auth_admin import router as auth_admin_router
from app.api.v1.tenant_admin_management import router as tenant_admin_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.organizations_multi_tenant import router as organizations_router
from app.api.v1.users import router as users_router
from app.api.v1 import companies, predictions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup"""
    logger.info("🚀 Starting Multi-Tenant Financial Risk API...")
    
    logger.info("📊 Initializing database...")
    try:
        create_tables()
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
    
    yield


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="🏦 Financial Default Risk Prediction API - Multi-Tenant",
        description="""
# 🎯 Enterprise Multi-Tenant Financial Risk Assessment Platform

## 📋 API Sections & Access Control

### 🔐 **USER AUTHENTICATION** (Public/User Access)
- User registration, login, organization joining
- Token management and logout

### 👨‍💼 **ADMIN AUTHENTICATION** (Super Admin Only)
- Admin user creation and management
- User impersonation and password resets
- Audit trails and bulk operations

### 🎯 **TENANT ADMIN MANAGEMENT** (Super Admin Only)
- **⭐ ATOMIC TENANT CREATION**: Create tenant + admin in one operation
- Existing user tenant admin assignment
- Tenant admin information and role management

### 🏢 **TENANT MANAGEMENT** (Super Admin Only)  
- Tenant CRUD operations
- Tenant statistics and admin management
- Multi-tenant data isolation

### 🏛️ **ORGANIZATION MANAGEMENT** (Tenant Admin + Org Admin)
- Organization CRUD within tenant scope
- Join token management and whitelisting
- Organization user management

### 👥 **USER MANAGEMENT** (Role-Based Scoped Access)
- Self-service profile management
- Admin user operations with proper scoping
- Role-based user administration

### 🏭 **COMPANIES** (Org Members + Above)
- Company data management
- Symbol-based company search
- Paginated company listings

### 📊 **PREDICTIONS** (Org Members + Above)
- **⭐ UNIFIED PREDICTION API**: Main ML prediction endpoint
- Annual and quarterly risk assessments
- Bulk prediction processing (sync/async)
- Prediction management and analytics

## 🔐 Role Hierarchy
1. **Super Admin** → Full system access
2. **Tenant Admin** → Tenant-scoped management
3. **Org Admin** → Organization-scoped management  
4. **Member** → Company & prediction access
5. **User** → Basic profile access

## 🚀 Quick Start for HDFC Bank Case
1. `POST /auth/login` (Super Admin)
2. `POST /tenant-admin/assign-existing-user` (Connect admin@hdfc.com)
3. `POST /organizations` (Create HDFC organizations)
4. `POST /predictions/unified-predict` (Run ML predictions)

---
*Version 2.0.0 - Built with FastAPI, PostgreSQL, and Advanced ML Models*
        """,
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Custom validation error handler with user-friendly messages"""
        errors = []
        for error in exc.errors():
            field = error["loc"][-1] if error["loc"] else "unknown"
            error_type = error["type"]
            
            if error_type == "missing":
                message = f"{field.replace('_', ' ').title()} is required"
            elif error_type == "string_too_short":
                message = f"{field.replace('_', ' ').title()} is too short"
            elif error_type == "string_too_long":
                message = f"{field.replace('_', ' ').title()} is too long"
            elif error_type == "value_error.email":
                message = "Please enter a valid email address"
            elif "password" in field.lower():
                message = "Password must be at least 8 characters long and contain letters and numbers"
            else:
                message = f"Invalid {field.replace('_', ' ')}"
            
            errors.append({
                "field": field,
                "message": message
            })
        
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "Validation failed",
                "message": "Please check the following fields and try again:",
                "errors": errors
            }
        )

    # Custom middleware for API timing and logging
    @app.middleware("http")
    async def add_timing_and_logging(request: Request, call_next):
        start_time = time.time()
        
        # Log incoming request
        logger.info(f"📥 {request.method} {request.url.path} - Started")
        
        # Process request
        response = await call_next(request)
        
        # Calculate timing
        process_time = time.time() - start_time
        timing_ms = round(process_time * 1000, 2)
        
        # Add timing header
        response.headers["X-Process-Time"] = str(timing_ms)
        
        # Log response with timing
        status_emoji = "✅" if response.status_code < 400 else "❌"
        logger.info(f"{status_emoji} {request.method} {request.url.path} - {response.status_code} ({timing_ms}ms)")
        
        return response

    # Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers - All follow /api/v1/ pattern with role-based access control
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["🔐 User Authentication"])
    app.include_router(auth_admin_router, prefix="/api/v1/auth", tags=["👨‍💼 Admin Authentication (Super Admin Only)"])
    app.include_router(tenant_admin_router, prefix="/api/v1", tags=["🎯 Tenant Admin Management (Super Admin Only)"])
    app.include_router(tenants_router, prefix="/api/v1/tenants", tags=["🏢 Tenant Management (Super Admin Only)"])
    app.include_router(organizations_router, prefix="/api/v1/organizations", tags=["🏛️ Organization Management (Tenant/Org Admin)"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["👥 User Management (Role-Based Access)"])
    app.include_router(companies.router, prefix="/api/v1/companies", tags=["🏭 Companies (Members+)"])
    app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["📊 Predictions (Members+)"])

    # Root endpoints
    @app.get("/")
    async def root():
        """API root endpoint with service information and final API structure."""
        return {
            "name": "🏦 Financial Default Risk Prediction API",
            "version": "2.0.0",
            "description": "Enterprise multi-tenant financial risk assessment platform",
            "docs": "/docs",
            "redoc": "/redoc",
            "api_sections": {
                "🔐 user_authentication": {
                    "prefix": "/api/v1/auth",
                    "access": "Public/User",
                    "endpoints": ["register", "login", "join", "refresh", "logout"]
                },
                "👨‍💼 admin_authentication": {
                    "prefix": "/api/v1/auth/admin",
                    "access": "Super Admin Only",
                    "endpoints": ["create-user", "impersonate", "force-password-reset", "audit", "bulk-activate"]
                },
                "🎯 tenant_admin_management": {
                    "prefix": "/api/v1/tenant-admin",
                    "access": "Super Admin Only",
                    "endpoints": ["create-tenant-with-admin ⭐", "assign-existing-user ⭐", "assign-user-to-organization ⭐", "admin-info", "remove-admin"],
                    "note": "⭐ Main APIs for HDFC Bank case"
                },
                "🏢 tenant_management": {
                    "prefix": "/api/v1/tenants",
                    "access": "Super Admin Only",
                    "endpoints": ["list", "create", "get", "update", "delete", "stats"],
                    "note": "Core tenant CRUD operations only - admin management moved to tenant-admin section"
                },
                "🏛️ organization_management": {
                    "prefix": "/api/v1/organizations",
                    "access": "Tenant Admin + Org Admin",
                    "endpoints": ["list", "create", "get", "update", "delete", "regenerate-token", "whitelist", "users"]
                },
                "👥 user_management": {
                    "prefix": "/api/v1/users",
                    "access": "Role-Based Scoped",
                    "endpoints": ["profile (self)", "list", "create", "get", "update", "delete", "role", "activate", "deactivate"]
                },
                "🏭 companies": {
                    "prefix": "/api/v1/companies",
                    "access": "Members+",
                    "endpoints": ["list", "create", "get", "search"]
                },
                "📊 predictions": {
                    "prefix": "/api/v1/predictions",
                    "access": "Members+",
                    "endpoints": ["unified-predict ⭐", "companies ⭐", "summary ⭐", "annual", "quarterly", "bulk", "async", "management"],
                    "note": "⭐ Core prediction APIs"
                }
            },
            "role_hierarchy": [
                "Super Admin → Full system access",
                "Tenant Admin → Tenant-scoped management", 
                "Org Admin → Organization-scoped management",
                "Member → Company & prediction access",
                "User → Basic profile access"
            ],
            "quick_start_hdfc": [
                "1. POST /auth/login (Super Admin)",
                "2. POST /tenant-admin/assign-existing-user (Connect admin@hdfc.com)",
                "3. POST /organizations (Create HDFC organizations)",
                "4. POST /predictions/unified-predict (Run ML predictions)"
            ]
        }

    @app.get("/health")
    async def health_check():
        """Health check endpoint for monitoring."""
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "financial-risk-api",
            "version": "2.0.0"
        }

    return app


# Create the app instance
app = create_app()
