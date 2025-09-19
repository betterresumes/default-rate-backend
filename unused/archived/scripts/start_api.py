from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import os
import uvicorn
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from src.database import create_tables, create_database_engine
from src.routers.auth_multi_tenant import router as auth_router
from src.routers.tenants import router as tenants_router
from src.routers.organizations_multi_tenant import router as organizations_router
from src.routers.users import router as users_router
from src.routers import companies, predictions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables on startup"""
    logger.info("🚀 Starting Multi-Tenant API server...")
    
    logger.info("📊 Initializing database...")
    try:
        create_tables()
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
    
    yield

# Create FastAPI app
app = FastAPI(
    title="Financial Default Risk Prediction API - Multi-Tenant",
    description="Multi-tenant financial default risk prediction platform",
    version="2.0.0",
    lifespan=lifespan
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

# Include routers
app.include_router(auth_router, prefix="/api", tags=["Authentication"])
app.include_router(tenants_router, prefix="/api", tags=["Tenant Management"])
app.include_router(organizations_router, prefix="/api", tags=["Organization Management"])
app.include_router(users_router, prefix="/api", tags=["User Management"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Multi-Tenant Financial Default Risk Prediction API",
        "version": "2.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "features": [
            "Multi-tenant architecture",
            "Enterprise tenant support",
            "Whitelist-based organization joining",
            "5-role permission system",
            "Complete data isolation"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "multi-tenant-api"
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
