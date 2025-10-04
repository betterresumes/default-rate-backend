"""
Main FastAPI application starting and configuration.
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
from app.middleware.rate_limiting import setup_rate_limiting, rate_limit_health, rate_limit_api
from app.middleware.security_headers import setup_security_headers
from app.api.v1.auth_multi_tenant import router as auth_router
from app.api.v1.auth_admin import router as auth_admin_router
from app.api.v1.tenant_admin_management import router as tenant_admin_router
from app.api.v1.tenants import router as tenants_router
from app.api.v1.organizations_multi_tenant import router as organizations_router
from app.api.v1.users import router as users_router
from app.api.v1 import companies, predictions
from app.api.v1.scaling import router as scaling_router
from app.api.v1.debug import debug_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and services on startup with comprehensive logging"""
    
    # Enhanced startup logging
    logger.info("=" * 60)
    logger.info("🚀 ACCUNODE API STARTUP")
    logger.info("=" * 60)
    
    # Environment information
    environment = os.getenv("ENVIRONMENT", "development")
    aws_region = os.getenv("AWS_REGION", "local")
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    
    logger.info(f"🌍 Environment: {environment}")
    logger.info(f"🏗️ AWS Region: {aws_region}")
    logger.info(f"🐛 Debug Mode: {debug_mode}")
    logger.info(f"📅 Started at: {datetime.utcnow().isoformat()}")
    logger.info(f"🐍 Python Version: {os.sys.version}")
    
    # Configuration verification
    logger.info("\n� Configuration Check:")
    from app.core.config import Config
    config = Config()
    
    # Check database configuration
    logger.info("�📊 Database Configuration:")
    if hasattr(config, 'DATABASE_URL') and config.DATABASE_URL:
        # Don't log full URL for security, just indicate it's configured
        db_host = "configured" if config.DATABASE_URL else "not configured"
        logger.info(f"   Database URL: {db_host}")
    else:
        logger.error("   ❌ DATABASE_URL not configured!")
    
    # Check Redis configuration
    logger.info("🔴 Redis Configuration:")
    redis_url = os.getenv("REDIS_URL", "")
    if redis_url:
        logger.info("   Redis URL: configured")
    else:
        logger.warning("   ⚠️ Redis URL not configured - rate limiting may fail")
    
    # Initialize database
    logger.info("\n📊 Initializing Database...")
    try:
        create_tables()
        logger.info("✅ Database: Connected and tables verified")
    except Exception as e:
        logger.error(f"❌ Database: Connection failed - {e}")
        logger.error("   This may cause API failures. Check DATABASE_URL configuration.")
    
    logger.info("🔄 Checking Redis connection...")
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        logger.info("✅ Redis: Connected successfully")
    except Exception as e:
        logger.error(f"❌ Redis: Connection failed - {e}")
    
    logger.info("🤖 Checking ML models...")
    try:
        from app.services.ml_service import ml_model
        from app.services.quarterly_ml_service import quarterly_ml_model
        
        annual_loaded = hasattr(ml_model, 'model') and ml_model.model is not None
        quarterly_loaded = hasattr(quarterly_ml_model, 'logistic_model') and quarterly_ml_model.logistic_model is not None
        
        if annual_loaded and quarterly_loaded:
            logger.info("✅ ML Models: Annual and Quarterly models loaded successfully")
        else:
            logger.warning("⚠️ ML Models: Some models may not be loaded properly")
    except Exception as e:
        logger.error(f"❌ ML Models: Loading failed - {e}")
    
    logger.info("👷 Checking Celery workers...")
    try:
        from app.workers.celery_app import celery_app
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if stats:
            worker_count = len(stats)
            logger.info(f"✅ Celery: {worker_count} worker(s) available")
        else:
            logger.warning("⚠️ Celery: No workers detected (background tasks may not process)")
    except Exception as e:
        logger.warning(f"⚠️ Celery: Worker check failed - {e}")
    
    logger.info("🔄 Starting Auto-Scaling Monitor...")
    try:
        import asyncio
        from app.workers.auto_scaling_monitor import start_auto_scaling_monitor
        
        # Start auto-scaling monitor as background task
        asyncio.create_task(start_auto_scaling_monitor())
        logger.info("✅ Auto-Scaling: Monitor started successfully")
    except Exception as e:
        logger.warning(f"⚠️ Auto-Scaling: Monitor startup failed - {e}")
    
    logger.info("🎯 API startup completed!")
    logger.info("📋 Available endpoints:")
    logger.info("   • Health Check: /health")
    logger.info("   • API Documentation: /docs")
    logger.info("   • API Root: /")
    logger.info("   • Main API: /api/v1/")
    logger.info("   • Auto-Scaling: /api/v1/scaling/")
    
    yield
    
    logger.info("🛑 Shutting down Default Rate Backend API...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    app = FastAPI(
        title="Default Rate Backend API",
        description="Financial risk assessment platform with machine learning predictions and multi-tenant architecture.",
        version="2.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Exception handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
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

    @app.middleware("http")
    async def add_timing_and_logging(request: Request, call_next):
        start_time = time.time()
        
        logger.info(f"📥 {request.method} {request.url.path} - Started")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        timing_ms = round(process_time * 1000, 2)
        
        response.headers["X-Process-Time"] = str(timing_ms)
        
        status_emoji = "✅" if response.status_code < 400 else "❌"
        logger.info(f"{status_emoji} {request.method} {request.url.path} - {response.status_code} ({timing_ms}ms)")
        
        return response

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            os.getenv("CORS_ORIGIN", "http://localhost:3000"),
            "https://accunode.ai",
            "https://client-eta-sepia.vercel.app"
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Setup comprehensive rate limiting
    setup_rate_limiting(app)
    
    # Setup security headers middleware
    setup_security_headers(app)

    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(auth_admin_router, prefix="/api/v1/auth", tags=["Admin Authentication"])
    app.include_router(tenant_admin_router, prefix="/api/v1", tags=["Tenant Admin Management"])
    app.include_router(tenants_router, prefix="/api/v1/tenants", tags=["Tenant Management"])
    app.include_router(organizations_router, prefix="/api/v1/organizations", tags=["Organization Management"])
    app.include_router(users_router, prefix="/api/v1/users", tags=["User Management"])
    app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
    app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["Predictions"])
    app.include_router(scaling_router, tags=["Auto-Scaling"])

    @app.get("/")
    @rate_limit_api
    async def root(request: Request):
        """API root endpoint with service information."""
        return {
            "name": "Default Rate Backend API",
            "version": "2.0.0",
            "description": "Financial risk assessment platform with machine learning predictions",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "status": "operational",
            "endpoints": {
                "health": "/health",
                "docs": "/docs", 
                "redoc": "/redoc",
                "api": "/api/v1"
            },
            "timestamp": datetime.utcnow().isoformat()
        }

    @app.get("/health")
    @rate_limit_health
    async def health_check(request: Request):
        """Comprehensive health check endpoint for monitoring."""
        import redis
        from sqlalchemy import text
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "default-rate-backend-api",
            "version": "2.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "services": {
                "database": {"status": "unknown", "connected": False},
                "redis": {"status": "unknown", "connected": False},
                "ml_models": {"status": "unknown", "loaded": False},
                "celery": {"status": "unknown", "available": False}
            },
            "system": {
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "disk_usage": 0.0
            }
        }
        
        overall_healthy = True
        
        try:
            from app.core.database import get_session_local
            SessionLocal = get_session_local()
            db = SessionLocal()
            result = db.execute(text("SELECT 1"))
            health_status["services"]["database"] = {
                "status": "healthy",
                "connected": True
            }
            db.close()
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "error",
                "connected": False,
                "error": str(e)
            }
            overall_healthy = False
        
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            r = redis.from_url(redis_url)
            r.ping()
            health_status["services"]["redis"] = {
                "status": "healthy",
                "connected": True
            }
        except Exception as e:
            health_status["services"]["redis"] = {
                "status": "error", 
                "connected": False,
                "error": "Connection failed"
            }
            overall_healthy = False
        
        try:
            from app.services.ml_service import ml_model
            from app.services.quarterly_ml_service import quarterly_ml_model
            
            annual_loaded = hasattr(ml_model, 'model') and ml_model.model is not None
            quarterly_loaded = hasattr(quarterly_ml_model, 'logistic_model') and quarterly_ml_model.logistic_model is not None
            
            if annual_loaded and quarterly_loaded:
                health_status["services"]["ml_models"] = {
                    "status": "healthy",
                    "loaded": True,
                    "models": ["annual_prediction", "quarterly_prediction"]
                }
            else:
                health_status["services"]["ml_models"] = {
                    "status": "warning",
                    "loaded": False,
                    "error": "Some models not loaded"
                }
        except Exception as e:
            health_status["services"]["ml_models"] = {
                "status": "error",
                "loaded": False,
                "error": "Model loading failed"
            }
            overall_healthy = False
        
        try:
            from app.workers.celery_app import celery_app
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            
            if stats:
                health_status["services"]["celery"] = {
                    "status": "healthy",
                    "available": True,
                    "workers": len(stats) if stats else 0
                }
            else:
                health_status["services"]["celery"] = {
                    "status": "warning",
                    "available": False,
                    "error": "No workers available"
                }
        except Exception as e:
            health_status["services"]["celery"] = {
                "status": "error",
                "available": False,
                "error": "Celery not available"
            }
        
        try:
            import psutil
            health_status["system"] = {
                "cpu_usage": round(psutil.cpu_percent(interval=0.1), 2),
                "memory_usage": round(psutil.virtual_memory().percent, 2),
                "disk_usage": round(psutil.disk_usage('/').percent, 2)
            }
        except ImportError:
            health_status["system"] = {
                "cpu_usage": "N/A",
                "memory_usage": "N/A", 
                "disk_usage": "N/A",
                "note": "psutil not installed - system metrics unavailable"
            }
        except Exception:
            health_status["system"] = {
                "cpu_usage": "Error",
                "memory_usage": "Error",
                "disk_usage": "Error"
            }
        
        if not overall_healthy:
            health_status["status"] = "degraded"
        
        return health_status

    return app


app = create_app()
