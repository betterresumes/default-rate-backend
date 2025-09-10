from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
import uvicorn
import logging
import redis
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()

from .database import create_tables, create_database_engine
from .celery_app import celery_app
from .routers import companies, predictions, auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_database_connection():
    """Check if database connection is working"""
    try:
        engine = create_database_engine()
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            result.fetchone()
        logger.info("✅ Database connection: HEALTHY")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection: FAILED - {str(e)}")
        return False

def check_redis_connection():
    """Check if Redis connection is working"""
    try:
        # Get Redis configuration from environment
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", "6379"))
        redis_db = int(os.getenv("REDIS_DB", "0"))
        redis_password = os.getenv("REDIS_PASSWORD", "")
        
        # Create Redis client
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password if redis_password else None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Test connection
        redis_client.ping()
        logger.info(f"✅ Redis connection: HEALTHY (Host: {redis_host}:{redis_port}, DB: {redis_db})")
        return True
    except Exception as e:
        logger.error(f"❌ Redis connection: FAILED - {str(e)}")
        return False

def check_celery_worker_connection():
    """Check if Celery workers are available"""
    try:
        # Get active workers
        active_workers = celery_app.control.inspect().active()
        if active_workers:
            worker_count = len(active_workers)
            worker_names = list(active_workers.keys())
            logger.info(f"✅ Celery workers: HEALTHY ({worker_count} workers active)")
            logger.info(f"   Active workers: {', '.join(worker_names)}")
            return True
        else:
            logger.warning("⚠️ Celery workers: NO ACTIVE WORKERS FOUND")
            return False
    except Exception as e:
        logger.error(f"❌ Celery worker connection: FAILED - {str(e)}")
        return False

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database tables and pre-load ML models on startup"""
    logger.info("🚀 Starting FastAPI server...")
    
    # Check all connections
    logger.info("🔍 Checking system connections...")
    
    db_status = check_database_connection()
    redis_status = check_redis_connection()
    
    # Initialize database
    logger.info("📊 Initializing database...")
    try:
        create_tables()
        logger.info("✅ Database tables created/verified")
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
    
    # Check Celery workers (after a short delay to allow workers to start)
    import asyncio
    await asyncio.sleep(2)  # Give workers time to connect
    worker_status = check_celery_worker_connection()
    
    # Pre-load ML models
    logger.info("🤖 Pre-loading ML models...")
    try:
        from .ml_service import ml_service
        test_ratios = {
            "debt_to_equity_ratio": 0.5,
            "current_ratio": 2.0,
            "quick_ratio": 1.5,
            "return_on_equity": 0.15,
            "return_on_assets": 0.08,
            "profit_margin": 0.10,
            "interest_coverage": 5.0,
            "fixed_asset_turnover": 1.2,
            "total_debt_ebitda": 2.5
        }
        ml_service.predict_default_probability(test_ratios)
        logger.info("✅ ML models pre-loaded successfully")
    except Exception as e:
        logger.warning(f"⚠️ ML model pre-loading warning: {e}")
    
    # Summary of system health
    logger.info("📋 System Health Summary:")
    logger.info(f"   Database: {'✅ HEALTHY' if db_status else '❌ UNHEALTHY'}")
    logger.info(f"   Redis: {'✅ HEALTHY' if redis_status else '❌ UNHEALTHY'}")
    logger.info(f"   Celery Workers: {'✅ HEALTHY' if worker_status else '⚠️ NO WORKERS'}")
    
    if not db_status:
        logger.error("🚨 CRITICAL: Database connection failed - API may not function properly")
    if not redis_status:
        logger.error("🚨 CRITICAL: Redis connection failed - Background tasks will not work")
    if not worker_status:
        logger.warning("🚨 WARNING: No Celery workers detected - Background tasks will queue but not process")
    
    logger.info("🎯 FastAPI server startup complete!")
    
    yield
    
    logger.info("🛑 Shutting down FastAPI server...")

app = FastAPI(
    title="Financial Default Risk Prediction API",
    description="FastAPI server for predicting corporate default risk using machine learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["authentication"]
)

app.include_router(
    companies.router,
    prefix="/api/companies",
    tags=["companies"]
)

app.include_router(
    predictions.router,
    prefix="/api/predictions",
    tags=["predictions"]
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Financial Default Risk Prediction API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health/workers")
async def worker_diagnostics():
    """Detailed Celery worker diagnostics"""
    try:
        # Get comprehensive worker information
        stats = celery_app.control.inspect().stats()
        active = celery_app.control.inspect().active()
        scheduled = celery_app.control.inspect().scheduled()
        reserved = celery_app.control.inspect().reserved()
        registered = celery_app.control.inspect().registered()
        
        return {
            "worker_count": len(stats) if stats else 0,
            "workers": {
                "stats": stats,
                "active_tasks": active,
                "scheduled_tasks": scheduled,
                "reserved_tasks": reserved,
                "registered_tasks": registered
            },
            "broker_url": celery_app.conf.broker_url,
            "result_backend": celery_app.conf.result_backend,
            "task_routes": celery_app.conf.task_routes
        }
    except Exception as e:
        return {
            "error": str(e),
            "worker_count": 0,
            "status": "failed"
        }

@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint"""
    import time
    
    start_time = time.time()
    
    # Check all connections
    db_status = check_database_connection()
    redis_status = check_redis_connection()
    worker_status = check_celery_worker_connection()
    
    # Get worker details
    worker_details = {}
    try:
        stats = celery_app.control.inspect().stats()
        active = celery_app.control.inspect().active()
        worker_details = {
            "stats": stats,
            "active_tasks": active,
            "worker_count": len(stats) if stats else 0
        }
    except Exception as e:
        worker_details = {"error": str(e)}
    
    response_time = round((time.time() - start_time) * 1000, 2)
    
    overall_status = "healthy" if all([db_status, redis_status]) else "unhealthy"
    
    return {
        "status": overall_status,
        "timestamp": time.time(),
        "response_time_ms": response_time,
        "version": "1.0.0",
        "services": {
            "database": {
                "status": "healthy" if db_status else "unhealthy",
                "connection": "✅ Connected" if db_status else "❌ Disconnected"
            },
            "redis": {
                "status": "healthy" if redis_status else "unhealthy",
                "connection": "✅ Connected" if redis_status else "❌ Disconnected",
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": os.getenv("REDIS_PORT", "6379"),
                "db": os.getenv("REDIS_DB", "0")
            },
            "celery_workers": {
                "status": "healthy" if worker_status else "warning",
                "connection": "✅ Workers Active" if worker_status else "⚠️ No Active Workers",
                "details": worker_details
            }
        },
        "environment": {
            "debug": os.getenv("DEBUG", "False"),
            "cors_origin": os.getenv("CORS_ORIGIN", "http://localhost:3000")
        }
    }

@app.get("/health/test-task")
async def test_celery_task():
    """Test Celery task execution"""
    try:
        # Send a test task (this won't actually process anything, just test connectivity)
        result = celery_app.send_task(
            'src.tasks.process_bulk_excel_task',
            args=['/tmp/test', 'test.xlsx'],
            countdown=1  # Delay execution by 1 second
        )
        
        return {
            "task_id": result.task_id,
            "status": "Task queued successfully",
            "message": "Celery worker connectivity is working"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed",
            "message": "Celery worker connectivity failed"
        }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"❌ Unhandled exception on {request.method} {request.url}: {exc}")
    logger.error(f"Exception details: {type(exc).__name__}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "details": str(exc) if os.getenv("DEBUG", "False").lower() == "true" else "An error occurred",
            "path": str(request.url.path),
            "method": request.method
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    logger.info(f"🚀 Starting server on port {port}")
    logger.info(f"📚 API docs: http://localhost:{port}/docs")
    logger.info(f"🔍 Health check: http://localhost:{port}/health")
    
    uvicorn.run(
        "src.app:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug",
        access_log=True
    )