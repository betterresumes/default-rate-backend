# 💻 Local Development

## 📋 **Section Overview**

Complete guide for setting up and working with AccuNode in a local development environment, including setup, workflows, testing, and debugging.

---

## 📚 **Documentation Files**

### 🛠️ **[SETUP.md](./SETUP.md)**
- Local environment prerequisites and installation
- Docker and Docker Compose setup
- Database initialization and configuration
- Environment variables and secrets

### 🔄 **[DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)**
- Git workflow and branching strategy
- Code standards and conventions
- Pull request process and reviews
- Continuous integration testing

### 🧪 **[TESTING_GUIDE.md](./TESTING_GUIDE.md)**
- Unit testing setup and best practices
- Integration testing with test databases
- API testing and validation
- Test coverage requirements

### 🐛 **[DEBUGGING.md](./DEBUGGING.md)**
- Local debugging setup with IDE integration
- Common issues and troubleshooting
- Performance profiling and optimization
- Log analysis and debugging techniques

### 📊 **[DATABASE_SETUP.md](./DATABASE_SETUP.md)**
- Local PostgreSQL installation and configuration
- Database migrations and seed data
- Redis setup for caching and sessions
- Database debugging and administration

### 🤖 **[ML_DEVELOPMENT.md](./ML_DEVELOPMENT.md)**
- Machine learning model development setup
- Model training and evaluation workflows
- Model versioning and deployment
- Feature engineering and data preprocessing

### 🔧 **[TOOLS_CONFIGURATION.md](./TOOLS_CONFIGURATION.md)**
- IDE setup (VS Code, PyCharm)
- Code formatting and linting configuration
- Development extensions and plugins
- Productivity tools and shortcuts

---

## 🚀 **Quick Start Guide**

### **For New Developers**
1. **Environment Setup**: Follow [SETUP.md](./SETUP.md) step by step
2. **Development Process**: Read [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)
3. **Testing**: Configure [TESTING_GUIDE.md](./TESTING_GUIDE.md)

### **For ML Engineers**
1. **Setup**: Complete [SETUP.md](./SETUP.md) and [DATABASE_SETUP.md](./DATABASE_SETUP.md)
2. **ML Workflow**: Study [ML_DEVELOPMENT.md](./ML_DEVELOPMENT.md)
3. **Testing**: Focus on [TESTING_GUIDE.md](./TESTING_GUIDE.md) ML sections

### **For DevOps Engineers**
1. **Local Infrastructure**: Setup [DATABASE_SETUP.md](./DATABASE_SETUP.md)
2. **CI/CD**: Configure [DEVELOPMENT_WORKFLOW.md](./DEVELOPMENT_WORKFLOW.md)
3. **Debugging**: Master [DEBUGGING.md](./DEBUGGING.md)

---

## 📋 **Prerequisites**

### **Required Software**
```bash
# Core Requirements
Python 3.11+              # Application runtime
Docker Desktop 4.0+       # Containerization
Git 2.30+                # Version control
Node.js 18+ (optional)    # For frontend development

# Database Requirements  
PostgreSQL 15+            # Primary database
Redis 7+                  # Cache and sessions

# Development Tools
VS Code or PyCharm        # Recommended IDEs
Postman/Insomnia         # API testing
pgAdmin/DBeaver          # Database administration
```

### **System Requirements**
| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **RAM** | 8GB | 16GB+ |
| **CPU** | 4 cores | 8+ cores |
| **Storage** | 20GB free | 50GB+ free |
| **OS** | macOS 10.15+, Ubuntu 20.04+, Windows 10+ | Latest versions |

---

## ⚡ **Quick Setup**

### **1. Clone Repository**
```bash
git clone https://github.com/betterresumes/default-rate-backend.git
cd default-rate-backend
```

### **2. Environment Setup**
```bash
# Copy environment template
cp .env.example .env.local

# Install Python dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.dev.txt
```

### **3. Database Setup**
```bash
# Start services with Docker Compose
docker-compose -f docker-compose.dev.yml up -d

# Run database migrations
alembic upgrade head

# Load seed data (optional)
python scripts/seed_data.py
```

### **4. Run Application**
```bash
# Start development server
uvicorn app.main:app --reload --port 8000

# Verify setup
curl http://localhost:8000/api/v1/health
```

---

## 🔧 **Development Tools**

### **Code Quality Tools**
```bash
# Code formatting
black .                   # Python code formatter
isort .                   # Import sorting

# Code linting
flake8 .                  # PEP 8 compliance
pylint app/               # Advanced linting
mypy app/                 # Type checking

# Security scanning
bandit -r app/            # Security vulnerability scanner
safety check              # Dependency vulnerability check
```

### **Testing Tools**
```bash
# Run tests
pytest                    # All tests
pytest -v                 # Verbose output
pytest --cov=app          # Coverage report
pytest -k "test_auth"     # Specific test pattern

# Load testing
locust -f tests/load_tests.py  # Performance testing
```

### **Database Tools**
```bash
# Database operations
alembic revision --autogenerate -m "Add new table"  # Create migration
alembic upgrade head                                 # Apply migrations
alembic downgrade -1                                # Rollback migration

# Database utilities
pg_dump accunode_dev > backup.sql                   # Backup database
psql accunode_dev < backup.sql                      # Restore database
```

---

## 🌐 **Local Environment URLs**

```bash
# Application URLs
API Server:      http://localhost:8000
API Docs:        http://localhost:8000/docs
Health Check:    http://localhost:8000/api/v1/health

# Database URLs
PostgreSQL:      localhost:5432 (accunode_dev)
Redis:           localhost:6379

# Admin Interfaces
pgAdmin:         http://localhost:5050 (if configured)
Redis Insight:   http://localhost:8001 (if configured)
```

---

## 📚 **Common Commands**

### **Development Server**
```bash
# Start with auto-reload
uvicorn app.main:app --reload --port 8000

# Start with specific environment
ENV=development uvicorn app.main:app --reload

# Start with debugging
python -m debugpy --listen 5678 -m uvicorn app.main:app --reload
```

### **Database Management**
```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Check migration status
alembic current

# View migration history
alembic history

# Reset database (CAUTION: destroys data)
alembic downgrade base && alembic upgrade head
```

### **Testing & Quality**
```bash
# Run specific test file
pytest tests/test_auth.py

# Run with coverage
pytest --cov=app --cov-report=html

# Run only integration tests
pytest -m "integration"

# Run performance tests
pytest -m "performance" --benchmark-only
```

---

## 🔍 **Debugging Setup**

### **VS Code Configuration**
```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/venv/bin/uvicorn",
            "args": ["app.main:app", "--reload", "--port", "8000"],
            "console": "integratedTerminal",
            "envFile": "${workspaceFolder}/.env.local",
            "python": "${workspaceFolder}/venv/bin/python"
        }
    ]
}
```

### **Environment Variables**
```bash
# .env.local example
DATABASE_URL=postgresql://postgres:password@localhost:5432/accunode_dev
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

---

**Last Updated**: October 5, 2025
