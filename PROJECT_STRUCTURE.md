# Project Structure

This document outlines the clean, production-ready project structure.

## 📁 Root Directory

```
backend/
├── 🏗️  Production Files
│   ├── main.py                    # Application entry point
│   ├── requirements.txt           # Main requirements (→ prod)
│   ├── requirements.prod.txt      # Production dependencies
│   ├── requirements.dev.txt       # Development dependencies
│   ├── Dockerfile                 # Production Docker image
│   ├── docker-compose.prod.yml    # Production compose file
│   └── render.yaml               # Render deployment config
│
├── ⚙️  Configuration
│   ├── .env.example              # Environment template
│   ├── .gitignore               # Git ignore rules
│   ├── .dockerignore            # Docker ignore rules
│   └── .railwayignore           # Railway ignore rules
│
├── 📋 Documentation
│   ├── README.md                 # Main project documentation
│   ├── PRODUCTION_CHECKLIST.md  # Deployment checklist
│   ├── docs/                    # API documentation
│   └── documentation/           # Detailed project docs
│
├── 🏢 Application
│   └── app/                     # Main application code
│       ├── __init__.py
│       ├── main.py              # FastAPI app factory
│       ├── api/                 # API routes
│       ├── core/                # Core config & database
│       ├── models/              # SQLAlchemy models
│       ├── schemas/             # Pydantic schemas
│       ├── services/            # Business logic
│       ├── utils/               # Utility functions
│       └── workers/             # Celery workers
│
├── 🚀 Operations
│   ├── deployment/              # Deployment configurations
│   │   ├── docker/             # Docker configs
│   │   ├── railway/            # Railway configs
│   │   └── scripts/            # Deployment scripts
│   ├── scripts/                # Utility scripts
│   ├── tests/                  # Test suite (placeholder)
│   └── data/                   # Data files & samples
│
├── 📦 Collections
│   ├── postman-collections/    # API testing collections
│   └── utils/                  # Legacy utility scripts
│
└── 🗃️  Archive
    └── unused/                 # Archived/unused files
        ├── documentation/      # Old markdown docs
        ├── test-files/         # Old test files & data
        ├── debug-scripts/      # Debug & analysis scripts
        └── old-scripts/        # Legacy shell scripts
```

## 🎯 Key Production Features

### ✅ Clean Structure
- All test files moved to `unused/test-files/`
- All debug scripts moved to `unused/debug-scripts/`
- All old documentation moved to `unused/documentation/`
- Main directory contains only production-essential files

### ✅ Proper Requirements Management
- `requirements.txt` → Points to production requirements
- `requirements.prod.txt` → Production-optimized dependencies
- `requirements.dev.txt` → Development tools & testing

### ✅ Production Configuration
- Environment-aware startup (`main.py`)
- Production-ready Docker setup
- Health check endpoints
- Proper logging configuration

### ✅ Documentation
- Comprehensive README
- Production deployment checklist
- Organized API documentation
- Clear project structure

### ✅ Development Workflow
```bash
# Development
pip install -r requirements.dev.txt
python main.py

# Production
pip install -r requirements.prod.txt
ENVIRONMENT=production python main.py

# Docker
docker-compose -f docker-compose.prod.yml up -d
```

## 📋 Deployment Ready

The codebase is now ready for production deployment with:
- ✅ Clean file organization
- ✅ Production-optimized dependencies  
- ✅ Environment-aware configuration
- ✅ Docker containerization
- ✅ Health monitoring
- ✅ Comprehensive documentation
- ✅ Development/Production separation

All non-essential files have been moved to the `unused/` directory for future reference while keeping the production codebase clean and maintainable.
