from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import os
import uvicorn
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database setup
from database import create_tables

# Import routers
from routers import companies, predictions

# Create FastAPI app with performance optimizations
app = FastAPI(
    title="Financial Default Risk Prediction API",
    description="FastAPI server for predicting corporate default risk using machine learning",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG", "False").lower() == "true" else None,
    redoc_url="/redoc" if os.getenv("DEBUG", "False").lower() == "true" else None
)

# Add gzip compression middleware for better performance
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("CORS_ORIGIN", "http://localhost:3000")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
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


@app.on_event("startup")
async def startup_event():
    """Initialize database tables and pre-load ML models on startup"""
    print("🚀 Starting FastAPI server...")
    print("📊 Initializing database...")
    try:
        create_tables()
        print("✅ Database tables created/verified")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
    
    # Pre-load ML models to avoid cold start delays
    print("🤖 Pre-loading ML models...")
    try:
        from ml_service import ml_service
        # This ensures models are loaded into memory at startup
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
        print("✅ ML models pre-loaded successfully")
    except Exception as e:
        print(f"⚠️ ML model pre-loading warning: {e}")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Financial Default Risk Prediction API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "OK",
        "message": "Server is running",
        "version": "1.0.0"
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    print(f"❌ Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "details": str(exc) if os.getenv("DEBUG") == "True" else "An error occurred"
        }
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    
    print(f"🚀 Starting server on port {port}")
    print(f"📝 Debug mode: {debug}")
    print(f"📚 API docs: http://localhost:{port}/docs")
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )