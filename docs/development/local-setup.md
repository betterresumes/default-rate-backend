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

# Node.js (for additional tooling)
node --version     # Should be 16+
npm --version
```

#### **Docker Method (Recommended)**
```bash
# Docker Desktop or Docker Engine
docker --version          # Should be 20.10+
docker-compose --version  # Should be 2.0+

# Verify Docker is running
docker ps
```

#### **Manual Setup Method**
```bash
# PostgreSQL 15+
psql --version

# Redis 7+
redis-server --version

# Additional development tools
curl --version
make --version
```

### **Development Tools (Optional but Recommended)**

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

---

## 🔧 **Manual Local Setup**

For developers who prefer a native setup or need more control over the development environment.

### **1. Database Setup**

**Install PostgreSQL:**
```bash
# macOS with Homebrew
brew install postgresql@15
brew services start postgresql@15

# Ubuntu/Debian
sudo apt update
sudo apt install postgresql-15 postgresql-contrib-15
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Windows
# Download from https://www.postgresql.org/download/windows/
```

**Create Development Database:**
```bash
# Create user and database
sudo -u postgres createuser --superuser $USER
createdb accunode_dev
createdb accunode_test

# Or use psql
psql postgres
CREATE DATABASE accunode_dev;
CREATE DATABASE accunode_test;
CREATE USER accunode_user WITH PASSWORD 'localdevpass';
GRANT ALL PRIVILEGES ON DATABASE accunode_dev TO accunode_user;
GRANT ALL PRIVILEGES ON DATABASE accunode_test TO accunode_user;
\q
```

**Install Redis:**
```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt install redis-server
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Windows
# Download from https://github.com/microsoftarchive/redis/releases
```

### **2. Python Environment Setup**

**Install Python 3.11+:**
```bash
# Check current version
python3 --version

# macOS with Homebrew
brew install python@3.11

# Ubuntu/Debian
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Windows
# Download from https://www.python.org/downloads/
```

**Create Virtual Environment:**
```bash
# Create virtual environment
python3.11 -m venv accunode-env

# Activate virtual environment
# macOS/Linux:
source accunode-env/bin/activate

# Windows:
accunode-env\Scripts\activate

# Verify activation
which python  # Should point to virtual environment
```

**Install Dependencies:**
```bash
# Ensure you're in the project root and venv is activated
cd accunode-backend

# Install development dependencies
pip install -r requirements.dev.txt

# Install pre-commit hooks
pre-commit install

# Verify installation
pip list | grep fastapi
pip list | grep sqlalchemy
```

### **3. Application Configuration**

**Environment Setup:**
```bash
# Copy and configure environment file
cp .env.example .env.local

# Edit configuration for local setup
nano .env.local  # or use your preferred editor
```

**.env.local (for manual setup):**
```bash
# Environment
ENVIRONMENT=development
DEBUG=true

# Database (local PostgreSQL)
DATABASE_URL=postgresql://accunode_user:localdevpass@localhost:5432/accunode_dev

# Redis (local Redis)
REDIS_URL=redis://localhost:6379/0

# Security (use secure keys in shared environments)
SECRET_KEY=local-dev-secret-key-123
JWT_SECRET_KEY=local-dev-jwt-secret-456

# Other settings...
```

**Database Initialization:**
```bash
# Set environment variables
export $(cat .env.local | xargs)

# Run migrations
alembic upgrade head

# Load sample data
python scripts/load_sample_data.py

# Create superuser
python scripts/create-super_Admin.py
```

### **4. Start Development Services**

**Terminal 1 - FastAPI Application:**
```bash
# Activate virtual environment
source accunode-env/bin/activate

# Set environment
export $(cat .env.local | xargs)

# Start FastAPI with hot reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Alternative: Use the make command if available
make dev
```

**Terminal 2 - Celery Worker:**
```bash
# Activate virtual environment
source accunode-env/bin/activate

# Set environment
export $(cat .env.local | xargs)

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
```

**Terminal 3 - Celery Beat (Optional):**
```bash
# Activate virtual environment
source accunode-env/bin/activate

# Set environment
export $(cat .env.local | xargs)

# Start Celery beat scheduler
celery -A app.workers.celery_app beat --loglevel=info
```

### **5. Verify Manual Setup**

```bash
# Test database connection
python -c "
import asyncpg
import asyncio

async def test_db():
    conn = await asyncpg.connect('postgresql://accunode_user:localdevpass@localhost:5432/accunode_dev')
    result = await conn.fetch('SELECT version()')
    print('Database:', result[0]['version'])
    await conn.close()

asyncio.run(test_db())
"

# Test Redis connection
python -c "
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
r.set('test_key', 'test_value')
print('Redis test:', r.get('test_key').decode())
r.delete('test_key')
"

# Test API endpoint
curl http://localhost:8000/health

# Check API documentation
open http://localhost:8000/docs
```

---

## 💾 **Database Configuration**

### **Development Database Schema**

**Initialize with Sample Data:**
```bash
# Run the complete database setup
python scripts/setup_dev_database.py
```

**scripts/setup_dev_database.py:**
```python
#!/usr/bin/env python3
"""
Development database setup script
Creates sample data for local development and testing
"""

import asyncio
import asyncpg
from datetime import datetime, timedelta
import uuid
from faker import Faker
import random

fake = Faker()

async def setup_development_database():
    # Connect to database
    conn = await asyncpg.connect(
        "postgresql://accunode_user:localdevpass@localhost:5432/accunode_dev"
    )
    
    print("🗄️  Setting up development database...")
    
    # Create sample tenant
    tenant_id = str(uuid.uuid4())
    await conn.execute("""
        INSERT INTO tenants (id, name, domain, is_active) 
        VALUES ($1, 'Development Tenant', 'dev.accunode.local', true)
        ON CONFLICT (domain) DO NOTHING
    """, tenant_id)
    
    # Create sample organization
    org_id = str(uuid.uuid4())
    await conn.execute("""
        INSERT INTO organizations (id, tenant_id, name, description, is_active) 
        VALUES ($1, $2, 'AccuNode Development', 'Development organization for testing', true)
        ON CONFLICT DO NOTHING
    """, org_id, tenant_id)
    
    # Create sample users
    users = []
    for i in range(5):
        user_id = str(uuid.uuid4())
        email = f"user{i+1}@accunode.dev"
        role = ['user', 'org_member', 'org_admin'][i % 3]
        
        await conn.execute("""
            INSERT INTO users (id, tenant_id, organization_id, email, username, 
                             first_name, last_name, role, is_active, is_verified) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, true, true)
            ON CONFLICT (email) DO NOTHING
        """, user_id, tenant_id, org_id, email, f"user{i+1}",
             fake.first_name(), fake.last_name(), role)
        
        users.append(user_id)
    
    # Create sample companies
    companies = []
    sectors = ['Technology', 'Healthcare', 'Financial Services', 'Energy', 'Consumer Goods']
    exchanges = ['NASDAQ', 'NYSE', 'LSE', 'TSE']
    
    for i in range(20):
        company_id = str(uuid.uuid4())
        symbol = fake.lexify(text='????', letters='ABCDEFGHIJKLMNOPQRSTUVWXYZ')
        name = fake.company()
        sector = random.choice(sectors)
        exchange = random.choice(exchanges)
        market_cap = random.randint(1000000000, 2000000000000)  # 1B to 2T
        
        await conn.execute("""
            INSERT INTO companies (id, organization_id, symbol, name, market_cap, 
                                 sector, country, exchange, is_active) 
            VALUES ($1, $2, $3, $4, $5, $6, 'USA', $7, true)
            ON CONFLICT (symbol) DO NOTHING
        """, company_id, org_id, symbol, name, market_cap, sector, exchange)
        
        companies.append(company_id)
    
    # Create sample annual predictions
    for company_id in companies:
        for year in ['2022', '2023']:
            prediction_id = str(uuid.uuid4())
            user_id = random.choice(users)
            
            # Generate realistic financial ratios
            long_term_debt_ratio = random.uniform(0.1, 0.8)
            debt_to_ebitda = random.uniform(0.5, 8.0)
            net_income_margin = random.uniform(-0.1, 0.3)
            ebit_interest = random.uniform(1.0, 50.0)
            roa = random.uniform(-0.05, 0.25)
            
            # Calculate probability (simplified model)
            probability = max(0.01, min(0.99, 
                0.2 + long_term_debt_ratio * 0.3 + 
                (debt_to_ebitda / 10) * 0.2 - 
                net_income_margin * 0.4 - 
                (ebit_interest / 100) * 0.2 - 
                roa * 0.3 + 
                random.uniform(-0.15, 0.15)
            ))
            
            risk_level = 'Low' if probability < 0.3 else 'Medium' if probability < 0.7 else 'High'
            
            await conn.execute("""
                INSERT INTO annual_predictions (
                    id, company_id, created_by, reporting_year,
                    long_term_debt_to_total_capital, total_debt_to_ebitda,
                    net_income_margin, ebit_to_interest_expense, return_on_assets,
                    probability, risk_level, confidence,
                    logistic_probability, step_probability, access_level
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 'organization')
                ON CONFLICT (company_id, reporting_year) DO NOTHING
            """, prediction_id, company_id, user_id, year,
                 long_term_debt_ratio, debt_to_ebitda, net_income_margin,
                 ebit_interest, roa, probability, risk_level, 
                 random.uniform(0.7, 0.95), probability + random.uniform(-0.05, 0.05),
                 probability + random.uniform(-0.03, 0.03))
    
    print(f"✅ Development database setup complete!")
    print(f"   - Created {len(companies)} sample companies")
    print(f"   - Created {len(users)} sample users")
    print(f"   - Created sample predictions for 2022-2023")
    print(f"   - Default login: user1@accunode.dev / password123")
    
    await conn.close()

if __name__ == "__main__":
    asyncio.run(setup_development_database())
```

### **Database Management Tools**

**Install Database Tools:**
```bash
# PostgreSQL CLI with autocompletion
pip install pgcli

# Redis CLI tools
pip install redis-cli

# Database migration tools (already in requirements.dev.txt)
pip install alembic
```

**Useful Database Commands:**
```bash
# Connect with pgcli (better than psql for development)
pgcli postgresql://accunode_user:localdevpass@localhost:5432/accunode_dev

# Quick database stats
psql postgresql://accunode_user:localdevpass@localhost:5432/accunode_dev -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Reset development database
python scripts/reset_dev_database.py

# Create database migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Downgrade migration (be careful!)
alembic downgrade -1
```

---

## 🧪 **Testing Setup**

### **Test Environment Configuration**

**Test Database Setup:**
```bash
# Create test database
createdb accunode_test

# Set test environment variables
export TEST_DATABASE_URL=postgresql://accunode_user:localdevpass@localhost:5432/accunode_test
export TESTING=true
```

**Install Testing Dependencies:**
```bash
# Already included in requirements.dev.txt
pip install pytest pytest-asyncio pytest-cov httpx
```

### **Running Tests**

**Basic Test Commands:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_predictions.py

# Run specific test function
pytest tests/test_api/test_predictions.py::test_create_annual_prediction

# Run tests with verbose output
pytest -v

# Run tests and stop on first failure
pytest -x

# Run tests in parallel (if you have pytest-xdist installed)
pytest -n auto
```

**Test Configuration (pytest.ini):**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --asyncio-mode=auto
markers =
    unit: Unit tests
    integration: Integration tests
    api: API tests
    slow: Slow running tests
    db: Tests that require database
asyncio_mode = auto
```

**Sample Test Structure:**
```
tests/
├── conftest.py              # Shared fixtures
├── test_core/
│   ├── test_config.py
│   ├── test_database.py
│   └── test_security.py
├── test_api/
│   ├── test_auth.py
│   ├── test_predictions.py
│   ├── test_companies.py
│   └── test_users.py
├── test_services/
│   ├── test_ml_service.py
│   └── test_bulk_upload.py
└── test_workers/
    ├── test_tasks.py
    └── test_celery_app.py
```

---

## 🔍 **Debugging & Profiling**

### **VS Code Debug Configuration**

**.vscode/launch.json:**
```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/accunode-env/bin/uvicorn",
            "args": [
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", "8000",
                "--reload"
            ],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env.local",
            "cwd": "${workspaceFolder}",
            "python": "${workspaceFolder}/accunode-env/bin/python"
        },
        {
            "name": "Pytest Debug",
            "type": "python",
            "request": "launch",
            "module": "pytest",
            "args": [
                "${workspaceFolder}/tests",
                "-v"
            ],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env.local",
            "cwd": "${workspaceFolder}",
            "python": "${workspaceFolder}/accunode-env/bin/python"
        },
        {
            "name": "Celery Worker Debug",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/accunode-env/bin/celery",
            "args": [
                "-A", "app.workers.celery_app",
                "worker",
                "--loglevel=debug",
                "--concurrency=1"
            ],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env.local",
            "cwd": "${workspaceFolder}",
            "python": "${workspaceFolder}/accunode-env/bin/python"
        }
    ]
}
```

### **Profiling Tools**

**Install Profiling Dependencies:**
```bash
# Performance profiling
pip install line_profiler memory_profiler py-spy

# HTTP request profiling  
pip install requests-toolbelt
```

**Enable Profiling in Development:**
```python
# In app/main.py - add middleware for development
if settings.ENVIRONMENT == "development":
    import time
    
    @app.middleware("http")
    async def add_process_time_header(request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
```

**Profile Specific Functions:**
```bash
# Line profiler
kernprof -l -v app/services/ml_service.py

# Memory profiler
python -m memory_profiler app/services/ml_service.py

# Live profiling with py-spy
py-spy top --pid $(pgrep -f "uvicorn")
```

---

## 🛠️ **Development Tools & Utilities**

### **Code Quality Tools**

**Install Development Tools:**
```bash
# Code formatting and linting (already in requirements.dev.txt)
pip install black isort flake8 mypy pre-commit

# Setup pre-commit hooks
pre-commit install
```

**Code Formatting:**
```bash
# Format code with Black
black app/ tests/

# Sort imports with isort  
isort app/ tests/

# Check code style with flake8
flake8 app/ tests/

# Type checking with mypy
mypy app/
```

**Pre-commit Configuration (.pre-commit-config.yaml):**
```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.1.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8
        args: ["--max-line-length=88", "--extend-ignore=E203"]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.0.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

### **API Development Tools**

**API Testing with HTTPie:**
```bash
# Install HTTPie
pip install httpie

# Test authentication
http POST localhost:8000/api/v1/auth/login email=user1@accunode.dev password=password123

# Test with JWT token
http GET localhost:8000/api/v1/users/me "Authorization:Bearer $TOKEN"

# Create prediction
http POST localhost:8000/api/v1/predictions/annual \
  "Authorization:Bearer $TOKEN" \
  company_symbol=AAPL \
  company_name="Apple Inc." \
  market_cap:=2800000000000 \
  sector=Technology \
  reporting_year=2023 \
  long_term_debt_to_total_capital:=0.28 \
  total_debt_to_ebitda:=1.2 \
  net_income_margin:=0.25 \
  ebit_to_interest_expense:=25.5 \
  return_on_assets:=0.18
```

**Database Query Tools:**
```bash
# Quick database queries during development
alias db="pgcli postgresql://accunode_user:localdevpass@localhost:5432/accunode_dev"
alias rediscli="redis-cli -h localhost -p 6379"

# Database shortcuts
db -c "SELECT COUNT(*) FROM annual_predictions;"
db -c "SELECT symbol, name FROM companies LIMIT 10;"
rediscli KEYS "session:*"
rediscli INFO memory
```

### **Makefile for Common Tasks**

**Makefile:**
```makefile
.PHONY: help dev test lint format clean install db-reset

# Default target
help:
	@echo "Available commands:"
	@echo "  dev         - Start development server"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo "  clean       - Clean cache files"
	@echo "  install     - Install dependencies"
	@echo "  db-reset    - Reset development database"

# Development server
dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run tests
test:
	pytest --cov=app --cov-report=html

# Linting
lint:
	flake8 app/ tests/
	mypy app/

# Format code
format:
	black app/ tests/
	isort app/ tests/

# Clean cache files
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage

# Install dependencies
install:
	pip install -r requirements.dev.txt
	pre-commit install

# Reset database
db-reset:
	python scripts/reset_dev_database.py
	python scripts/setup_dev_database.py

# Docker commands
docker-build:
	docker-compose -f docker-compose.dev.yml build

docker-up:
	docker-compose -f docker-compose.dev.yml up -d

docker-down:
	docker-compose -f docker-compose.dev.yml down

docker-logs:
	docker-compose -f docker-compose.dev.yml logs -f api
```

---

## 🚨 **Troubleshooting**

### **Common Issues & Solutions**

**1. Database Connection Issues**
```bash
# Problem: Cannot connect to PostgreSQL
# Solution 1: Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgres  # macOS

# Solution 2: Check connection parameters
psql postgresql://accunode_user:localdevpass@localhost:5432/accunode_dev

# Solution 3: Reset database credentials
sudo -u postgres psql
ALTER USER accunode_user PASSWORD 'newpassword';
\q
```

**2. Redis Connection Issues**
```bash
# Problem: Cannot connect to Redis
# Solution 1: Check if Redis is running
redis-cli ping  # Should return PONG

# Solution 2: Start Redis service
sudo systemctl start redis-server  # Linux
brew services start redis  # macOS

# Solution 3: Check Redis configuration
redis-cli INFO server
```

**3. Python Import Errors**
```bash
# Problem: ModuleNotFoundError
# Solution 1: Check virtual environment
which python  # Should point to your venv

# Solution 2: Check PYTHONPATH
export PYTHONPATH=/path/to/accunode-backend:$PYTHONPATH

# Solution 3: Reinstall dependencies
pip install -r requirements.dev.txt
```

**4. Migration Issues**
```bash
# Problem: Alembic migration errors
# Solution 1: Check current migration state
alembic current
alembic history

# Solution 2: Reset migrations (CAUTION: loses data)
alembic downgrade base
alembic upgrade head

# Solution 3: Create new migration
alembic revision --autogenerate -m "Fix migration issue"
```

**5. Docker Issues**
```bash
# Problem: Docker container won't start
# Solution 1: Check Docker status
docker ps -a
docker-compose -f docker-compose.dev.yml logs api

# Solution 2: Rebuild containers
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up --build

# Solution 3: Clean Docker system
docker system prune -f
docker volume prune -f
```

### **Performance Issues**

**1. Slow Database Queries**
```sql
-- Check for slow queries in development
SELECT 
    query,
    calls,
    total_time,
    mean_time
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

**2. High Memory Usage**
```bash
# Monitor Python memory usage
python -m memory_profiler app/main.py

# Monitor system resources
htop  # or top on systems without htop
```

**3. Slow Docker Performance**
```bash
# Problem: Docker running slowly on macOS
# Solution: Increase Docker Desktop resources
# Docker Desktop > Preferences > Resources
# Increase CPU and Memory allocation

# Problem: Slow file sync in Docker volumes
# Solution: Use delegated or cached volume mounts
# volumes:
#   - .:/app:delegated
```

### **Development Environment Reset**

**Complete Environment Reset:**
```bash
#!/bin/bash
# complete_reset.sh - Reset entire development environment

echo "🔄 Resetting AccuNode development environment..."

# Stop all services
docker-compose -f docker-compose.dev.yml down -v 2>/dev/null || true

# Clean Docker resources
docker system prune -f
docker volume prune -f

# Reset Python environment
deactivate 2>/dev/null || true
rm -rf accunode-env/
python3.11 -m venv accunode-env
source accunode-env/bin/activate

# Reinstall dependencies
pip install -r requirements.dev.txt

# Reset databases
dropdb accunode_dev 2>/dev/null || true
dropdb accunode_test 2>/dev/null || true
createdb accunode_dev
createdb accunode_test

# Restart Redis
redis-cli FLUSHALL

# Run setup
python scripts/setup_dev_database.py

echo "✅ Development environment reset complete!"
echo "🚀 Start development with: make dev"
```

---

**Last Updated**: October 5, 2023  
**Setup Version**: 2.0
