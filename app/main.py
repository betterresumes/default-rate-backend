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
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from app.core.database import create_tables
from app.api.v1.auth_multi_tenant import router as auth_router
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
        title="Financial Default Risk Prediction API - Multi-Tenant",
        description="Enterprise-grade multi-tenant financial default risk prediction platform",
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

    # Middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include API routers - All follow /api/v1/ pattern
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(tenants_router, prefix="/api/v1/tenants", tags=["Tenant Management"])
    app.include_router(organizations_router, prefix="/api/v1/organizations", tags=["Organization Management"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["User Management"])
    app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
    app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])

    # Root endpoints
    @app.get("/")
    async def root():
        """API root endpoint with service information."""
        return {
            "name": "Financial Default Risk Prediction API",
            "version": "2.0.0",
            "description": "Enterprise multi-tenant financial risk assessment platform",
            "docs": "/docs",
            "redoc": "/redoc",
            "endpoints": {
                "authentication": "/api/v1/auth",
                "tenants": "/api/v1/tenants",
                "organizations": "/api/v1/organizations", 
                "users": "/api/v1/users",
                "companies": "/api/v1/companies",
                "predictions": "/api/v1/predictions"
            }
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
