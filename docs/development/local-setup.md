# 💻 Local Development Setup Guide

> Important configuration (matches `docker-compose.dev.yml`)
>
> - PostgreSQL: db=accunode_development, user=admin, password=dev_password_123, host=postgres (inside containers) or localhost (from host)
> - Redis URL: redis://default:dev_redis_password@redis:6379 (inside containers) or redis://default:dev_redis_password@localhost:6379 (from host)
> - App env files: use `.env.development` or `.env.local` (the app reads `DATABASE_URL` and `REDIS_URL` directly)
> - Service names: api, worker, postgres, redis, localstack
> - Logs: `docker-compose -f docker-compose.dev.yml logs -f api`
>
> Optional components: Alembic migrations, pgAdmin, and redis-commander are not included by default. Use your own tools or extend compose if needed.

## 📋 **Table of Contents**
1. [Development Environment Overview](#development-environment-overview)
2. [Prerequisites & System Requirements](#prerequisites--system-requirements)
3. [Docker Development Setup](#docker-development-setup)
4. [Manual Local Setup](#manual-local-setup)
5. [Database Configuration](#database-configuration)
6. [Environment Configuration](#environment-configuration)
7. [Development Tools & Utilities](#development-tools--utilities)
8. [Testing Setup](#testing-setup)
9. [Debugging & Profiling](#debugging--profiling)
10. [Troubleshooting](#troubleshooting)

---

## 🏗️ **Development Environment Overview**

AccuNode provides multiple ways to set up a local development environment, with Docker Compose being the recommended approach for consistency and ease of setup.

### **Development Architecture**

```
┌─────────────────────────────────────────────────────────┐
│                Local Development                        │
├─────────────────────────────────────────────────────────┤
│  FastAPI App (localhost:8000)                          │
│  ├── Hot Reload Enabled                                │
│  ├── Debug Mode Active                                 │
│  └── API Documentation (localhost:8000/docs)           │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL (localhost:5432)                           │
│  ├── Development Database                              │
│  ├── Sample Data Loaded                               │
│  └── pgAdmin Available (localhost:5050)               │
├─────────────────────────────────────────────────────────┤
│  Redis (localhost:6379)                                │
│  ├── Cache & Session Store                            │
│  ├── Celery Task Queue                                │
│  └── Redis Commander (localhost:8081)                 │
├─────────────────────────────────────────────────────────┤
│  Celery Worker                                          │
│  ├── Background Task Processing                        │
│  ├── ML Model Inference                               │
│  └── Bulk Processing                                   │
└─────────────────────────────────────────────────────────┘
```

### **Available Development Options**

| Method | Pros | Cons | Best For |
|--------|------|------|----------|
| **Docker Compose** | Consistent environment, easy setup, includes all services | Requires Docker, may be slower on some systems | New developers, full-stack testing |
| **Manual Setup** | Native performance, easier debugging, flexible configuration | Complex setup, dependency management | Experienced developers, core development |
| **Hybrid Setup** | Best of both worlds, selective containerization | More complex configuration | Advanced users |

---

## ✅ **Prerequisites & System Requirements**

### **System Requirements**

**Minimum Requirements:**
- **OS**: macOS 10.15+, Windows 10+, or Ubuntu 18.04+
- **CPU**: 2+ cores recommended
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 10GB available space
- **Network**: Reliable internet connection for package downloads

**Recommended Requirements:**
- **CPU**: 4+ cores (Intel i5/i7, AMD Ryzen 5/7, or Apple M1/M2)
- **RAM**: 16GB+ for comfortable development
- **Storage**: SSD with 20GB+ available space

### **Required Software**

#### **Core Dependencies (All Methods)**
```bash
# Git (version control)
git --version  # Should be 2.20+

# Python 3.11+ 
python3 --version  # Should be 3.11+
pip3 --version

#### **Docker Method (Recommended)**
```bash
# Docker Desktop or Docker Engine
docker --version          # Should be 20.10+
docker-compose --version  # Should be 2.0+

# Verify Docker is running
docker ps
```



```bash
# Code editors with Python support
code --version      # VS Code
pycharm --version   # PyCharm

# API testing tools
curl --version
# Or install Postman, Insomnia, HTTPie

# Database management
pgcli --version     # PostgreSQL CLI with autocompletion
redis-cli --version

# Git workflow tools
gh --version        # GitHub CLI
```

---

## 🐳 **Docker Development Setup**

### **Quick Start (Recommended)**

**1. Clone the Repository**
```bash
# Clone the main repository
git clone https://github.com/your-org/accunode-backend.git
cd accunode-backend

# Verify you're on the correct branch
git branch -a
git checkout develop  # or main, depending on your workflow
```

**2. Environment Configuration**
```bash
# Copy environment template
cp .env.example .env.dev

# Edit the development environment file
# The defaults should work for local development
nano .env.dev  # or use your preferred editor
```

**3. Start Development Environment**
```bash
# Start all services with Docker Compose
docker-compose -f docker-compose.dev.yml up -d

# Verify all services are running
docker-compose -f docker-compose.dev.yml ps

# Check service logs
docker-compose -f docker-compose.dev.yml logs -f api
```

**4. Initialize the Database**
```bash
# Run database migrations
docker-compose -f docker-compose.dev.yml exec api alembic upgrade head

# Load sample data (optional)
docker-compose -f docker-compose.dev.yml exec api python scripts/load_sample_data.py

# Create a superuser account
docker-compose -f docker-compose.dev.yml exec api python scripts/create-super_Admin.py
```

**5. Verify Setup**
```bash
# Test API is accessible
curl http://localhost:8000/health

# Open API documentation
open http://localhost:8000/docs  # macOS
# or visit http://localhost:8000/docs in your browser
```

### **Docker Compose Configuration**

**docker-compose.dev.yml:**
```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: accunode-postgres-dev
    environment:
      POSTGRES_DB: accunode_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: devpassword
      POSTGRES_INITDB_ARGS: "--auth-host=scram-sha-256"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - accunode-dev

  # Redis Cache & Queue
  redis:
    image: redis:7-alpine
    container_name: accunode-redis-dev
    command: redis-server --appendonly yes --requirepass devredispass
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
    networks:
      - accunode-dev

  # FastAPI Application
  api:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: accunode-api-dev
    env_file:
      - .env.dev
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - /app/__pycache__  # Exclude Python cache
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://postgres:devpassword@postgres:5432/accunode_dev
      - REDIS_URL=redis://:devredispass@redis:6379
      - PYTHONPATH=/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - accunode-dev

  # Celery Worker
  worker:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: accunode-worker-dev
    env_file:
      - .env.dev
    volumes:
      - .:/app
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    environment:
      - ENVIRONMENT=development
      - DATABASE_URL=postgresql://postgres:devpassword@postgres:5432/accunode_dev
      - REDIS_URL=redis://:devredispass@redis:6379
      - PYTHONPATH=/app
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=2
    networks:
      - accunode-dev

  # Celery Beat (Scheduler)
  beat:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: accunode-beat-dev
    env_file:
      - .env.dev
    volumes:
      - .:/app
    depends_on:
      - redis
    environment:
      - ENVIRONMENT=development
      - REDIS_URL=redis://:devredispass@redis:6379
      - PYTHONPATH=/app
    command: celery -A app.workers.celery_app beat --loglevel=info
    networks:
      - accunode-dev

  # pgAdmin (Database Management UI)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: accunode-pgadmin-dev
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@accunode.dev
      PGADMIN_DEFAULT_PASSWORD: adminpassword
      PGADMIN_CONFIG_SERVER_MODE: 'False'
    ports:
      - "5050:80"
    depends_on:
      - postgres
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    networks:
      - accunode-dev

  # Redis Commander (Redis Management UI)
  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: accunode-redis-commander-dev
    environment:
      - REDIS_HOSTS=local:redis:6379:0:devredispass
    ports:
      - "8081:8081"
    depends_on:
      - redis
    networks:
      - accunode-dev

volumes:
  postgres_data:
  redis_data:
  pgadmin_data:

networks:
  accunode-dev:
    driver: bridge
```

**Dockerfile.dev:**
```dockerfile
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.dev.txt .
RUN pip install --no-cache-dir -r requirements.dev.txt

# Copy application code
COPY . .

# Create non-root user for development
RUN adduser --disabled-password --gecos '' devuser && \
    chown -R devuser:devuser /app
USER devuser

# Expose port
EXPOSE 8000

# Default command (overridden in docker-compose)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### **Development Environment File**

**.env.dev:**
```bash
# =============================================================================
# AccuNode Development Environment Configuration
# =============================================================================

# Environment
ENVIRONMENT=development
DEBUG=true

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Database Configuration
DATABASE_URL=postgresql://postgres:devpassword@localhost:5432/accunode_dev
DATABASE_ECHO=false  # Set to true for SQL query logging

# Redis Configuration
REDIS_URL=redis://:devredispass@localhost:6379/0

# Authentication & Security
SECRET_KEY=dev-secret-key-change-in-production-abcdef123456
JWT_SECRET_KEY=dev-jwt-secret-key-change-in-production-xyz789
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=1440  # 24 hours
REFRESH_TOKEN_EXPIRATION_DAYS=30

# CORS Configuration (permissive for development)
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000","http://127.0.0.1:3000"]
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET","POST","PUT","DELETE","PATCH","OPTIONS"]
CORS_ALLOW_HEADERS=["*"]

# Logging Configuration
LOG_LEVEL=DEBUG
LOG_FORMAT=detailed
ENABLE_REQUEST_LOGGING=true

# ML Models Configuration
MODEL_PATH=/app/app/models
ENABLE_MODEL_CACHING=true
MODEL_CACHE_TTL=3600

# Email Configuration (for testing)
EMAIL_PROVIDER=console  # Logs emails to console instead of sending
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
EMAIL_FROM_ADDRESS=noreply@accunode.dev

# File Upload Configuration
UPLOAD_MAX_SIZE=10485760  # 10MB
UPLOAD_ALLOWED_EXTENSIONS=["csv","xlsx","xls"]

# Rate Limiting (relaxed for development)
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=1000

# Testing Configuration
TEST_DATABASE_URL=postgresql://postgres:devpassword@localhost:5432/accunode_test
PYTEST_TIMEOUT=300

# Development Tools
ENABLE_PROFILING=true
ENABLE_HOT_RELOAD=true
SHOW_TRACEBACK=true
```

### **Common Docker Commands**

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Stop all services
docker-compose -f docker-compose.dev.yml down

# Rebuild and restart services
docker-compose -f docker-compose.dev.yml up -d --build

# View logs
docker-compose -f docker-compose.dev.yml logs -f api
docker-compose -f docker-compose.dev.yml logs -f worker

# Execute commands in running container
docker-compose -f docker-compose.dev.yml exec api bash
docker-compose -f docker-compose.dev.yml exec api python manage.py shell

# Run database migrations
docker-compose -f docker-compose.dev.yml exec api alembic upgrade head

# Run tests
docker-compose -f docker-compose.dev.yml exec api pytest

# Access PostgreSQL
docker-compose -f docker-compose.dev.yml exec postgres psql -U postgres -d accunode_dev

# Access Redis CLI
docker-compose -f docker-compose.dev.yml exec redis redis-cli -a devredispass

# Clean up (removes containers, networks, volumes)
docker-compose -f docker-compose.dev.yml down -v --remove-orphans
```