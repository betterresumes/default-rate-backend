# 🚀 AccuNode Local Development Setup

## Overview

This guide sets up a complete local development environment for AccuNode using Docker, allowing you to:
- Develop on the `prod-dev` branch locally
- Test thoroughly before merging to `prod` 
- Auto-deploy to AWS when code is merged to `prod`

## Development Workflow

```
1. Develop in `prod-dev` branch → 2. Test locally with Docker → 3. Merge to `prod` → 4. Auto-deploy to AWS
```

---

## 🛠️ Prerequisites

### Required Software
- **Docker Desktop** (latest version)
- **Git** 
- **Code Editor** (VS Code recommended)

### Verify Installation
```bash
docker --version
docker-compose --version  # or docker compose version
git --version
```

---

## 🚀 Quick Start

### 1. Clone and Switch to Development Branch
```bash
git checkout prod-dev
git pull origin prod-dev
```

### 2. Start Development Environment
```bash
# Run the setup script (first time only)
./scripts/dev-setup.sh

# Or start manually
docker-compose -f docker-compose.dev.yml up -d
```

### 3. Access Your Application
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Database**: localhost:5432
- **Redis**: localhost:6379

---

## 📋 Available Services

### Core Services
| Service | Port | Purpose |
|---------|------|---------|
| FastAPI API | 8000 | Main application server |
| PostgreSQL | 5432 | Development database |
| Redis | 6379 | Caching and task queue |
| Celery Worker | - | Background task processing |
| LocalStack | 4566 | AWS services simulation |

### Service Configuration
- **Database**: `accunode_development` 
- **User**: `admin`
- **Password**: `dev_password_123`
- **Redis Password**: `dev_redis_password`

---

## 🔧 Development Commands

### Service Management
```bash
# Start all services
./scripts/dev-setup.sh

# View logs (all services)
./scripts/dev-logs.sh

# View logs (specific service)
./scripts/dev-logs.sh api
./scripts/dev-logs.sh postgres

# Restart services
./scripts/dev-restart.sh

# Stop all services
./scripts/dev-stop.sh
```

### Database Operations
```bash
# Connect to database
./scripts/dev-db.sh

# Using direct connection
psql -h localhost -U admin -d accunode_development -p 5432
# Password: dev_password_123
```

### Testing
```bash
# Run all tests
./scripts/dev-test.sh

# Run specific test file
./scripts/dev-test.sh tests/test_auth.py

# Run tests with coverage
docker-compose -f docker-compose.dev.yml exec api pytest --cov=app --cov-report=html
```

---

## 🏗️ Project Structure

```
backend/
├── docker-compose.dev.yml      # Development services
├── Dockerfile.dev              # Development container
├── .env.development            # Development environment variables
├── scripts/                    # Development helper scripts
│   ├── dev-setup.sh           # Initial setup
│   ├── dev-stop.sh            # Stop services  
│   ├── dev-logs.sh            # View logs
│   ├── dev-restart.sh         # Restart services
│   ├── dev-db.sh              # Connect to database
│   ├── dev-test.sh            # Run tests
│   └── init_db.sql            # Database initialization
├── app/                        # Application code
├── requirements.dev.txt        # Development dependencies
└── docs/                       # Documentation
```

---

## 🔄 Development Workflow

### Daily Development
1. **Start services**: `./scripts/dev-setup.sh`
2. **Make code changes** (auto-reloads in Docker)
3. **Test your changes**: `./scripts/dev-test.sh`
4. **Check logs**: `./scripts/dev-logs.sh api`
5. **Commit and push** to `prod-dev`

### Code Changes with Hot Reload
- Changes to Python files automatically reload the server
- Database schema changes may require container restart
- New dependencies require rebuilding: `docker-compose -f docker-compose.dev.yml build`

### Testing Before Production
```bash
# Run full test suite
./scripts/dev-test.sh

# Test specific functionality
./scripts/dev-test.sh tests/test_predictions.py

# Manual testing via API docs
open http://localhost:8000/docs
```

### Deploy to Production
```bash
# Switch to prod branch
git checkout prod

# Merge your changes from prod-dev
git merge prod-dev

# Push to trigger deployment
git push origin prod
```

---

## 🗄️ Database Management

### Connection Details
```bash
Host: localhost
Port: 5432
Database: accunode_development  
Username: admin
Password: dev_password_123
```

### Common Database Tasks
```bash
# Connect to database
./scripts/dev-db.sh

# View tables
\dt

# Check table structure
\d organizations

# Run custom queries
SELECT * FROM tenants LIMIT 5;

# Exit database
\q
```

### Reset Database
```bash
# Stop services and remove volumes
docker-compose -f docker-compose.dev.yml down -v

# Start fresh
./scripts/dev-setup.sh
```

---

## 🧪 Testing

### Test Types
- **Unit Tests**: Individual function testing
- **Integration Tests**: API endpoint testing  
- **Database Tests**: Model and query testing

### Running Tests
```bash
# All tests with coverage
./scripts/dev-test.sh

# Specific test file
./scripts/dev-test.sh tests/test_auth.py

# Specific test function
./scripts/dev-test.sh tests/test_auth.py::test_login

# With verbose output
docker-compose -f docker-compose.dev.yml exec api pytest -v -s
```

### Writing Tests
Create test files in `tests/` directory:
```python
# tests/test_example.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
```

---

## 🔍 Debugging

### View Application Logs
```bash
# API logs
./scripts/dev-logs.sh api

# All service logs
./scripts/dev-logs.sh

# Follow logs in real-time
docker-compose -f docker-compose.dev.yml logs -f api
```

### Debug API Issues
1. **Check service status**: `docker-compose -f docker-compose.dev.yml ps`
2. **View API logs**: `./scripts/dev-logs.sh api`
3. **Test endpoints**: Visit http://localhost:8000/docs
4. **Connect to container**: `docker-compose -f docker-compose.dev.yml exec api bash`

### Debug Database Issues
```bash
# Check PostgreSQL logs
./scripts/dev-logs.sh postgres

# Connect and verify data
./scripts/dev-db.sh

# Check if tables exist
\dt

# Verify connection
SELECT version();
```

---

## 🌐 Environment Variables

### Development Configuration
File: `.env.development`
```bash
# Application
ENVIRONMENT=development
DEBUG=true
PORT=8000

# Database  
DATABASE_URL=postgresql://admin:dev_password_123@localhost:5432/accunode_development

# Redis
REDIS_URL=redis://default:dev_redis_password@localhost:6379

# JWT (development only)
JWT_SECRET_KEY=dev_jwt_secret_key_not_for_production_use_only
```

### Override for Local Testing
Create `.env.local` (ignored by git):
```bash
# Local overrides
DEBUG=true
LOG_LEVEL=debug
```

---

## 🚨 Troubleshooting

### Common Issues

#### Docker Services Won't Start
```bash
# Check Docker is running
docker info

# Check port conflicts
netstat -an | grep :8000
netstat -an | grep :5432

# Clean restart
docker-compose -f docker-compose.dev.yml down
docker system prune -f
./scripts/dev-setup.sh
```

#### Database Connection Failed
```bash
# Check PostgreSQL container
docker-compose -f docker-compose.dev.yml logs postgres

# Verify database is running
docker-compose -f docker-compose.dev.yml ps postgres

# Reset database
docker-compose -f docker-compose.dev.yml down -v
./scripts/dev-setup.sh
```

#### API Not Loading Changes
```bash
# Check if auto-reload is working
./scripts/dev-logs.sh api

# Restart API service
./scripts/dev-restart.sh api

# Rebuild if dependencies changed
docker-compose -f docker-compose.dev.yml build api
```

#### Import Errors
```bash
# Check Python path in container
docker-compose -f docker-compose.dev.yml exec api python -c "import sys; print(sys.path)"

# Install missing dependencies
docker-compose -f docker-compose.dev.yml exec api pip install package_name

# Or add to requirements.dev.txt and rebuild
docker-compose -f docker-compose.dev.yml build api
```

---

## 📈 Performance Tips

### Development Optimization
- **Use Docker volumes** for fast file sync
- **Enable hot reload** for instant changes
- **Limit log verbosity** in production mode
- **Use database connection pooling**

### Resource Management
```bash
# Check container resource usage
docker stats

# Clean unused containers/images
docker system prune -f

# Monitor database connections
./scripts/dev-db.sh
SELECT * FROM pg_stat_activity;
```

---

## 🔒 Security Notes

### Development vs Production
- **Development uses simple passwords** (dev_password_123)
- **JWT keys are not secure** (development only)
- **Debug mode is enabled** (detailed error messages)
- **Rate limiting is relaxed** (higher limits)

### Never in Production
- Do not use `.env.development` in production
- Change all passwords and secrets for production
- Disable debug mode in production
- Enable proper rate limiting and security headers

---

## 🚀 Deployment Workflow

### Complete Development Cycle
```bash
# 1. Start development
git checkout prod-dev
./scripts/dev-setup.sh

# 2. Develop and test locally  
# Make changes...
./scripts/dev-test.sh

# 3. Commit changes
git add .
git commit -m "feat: add new feature"
git push origin prod-dev

# 4. Deploy to production
git checkout prod
git merge prod-dev
git push origin prod  # 🚀 Triggers AWS deployment!
```

### Deployment Verification
After pushing to `prod`:
1. **Check GitHub Actions**: Verify deployment pipeline
2. **Monitor ECS**: Check service deployment
3. **Test production API**: Verify endpoints work
4. **Check logs**: Monitor for errors

---

## 🆘 Getting Help

### Documentation Hierarchy
1. **This guide** - Local development setup
2. **`docs/team/TEAM_ONBOARDING_GUIDE.md`** - Complete team guide  
3. **`docs/aws/`** - AWS infrastructure docs
4. **`docs/application/`** - API documentation

### Quick Commands Reference
```bash
# Setup
./scripts/dev-setup.sh

# Daily use
./scripts/dev-logs.sh
./scripts/dev-db.sh  
./scripts/dev-test.sh

# Troubleshooting
./scripts/dev-restart.sh
./scripts/dev-stop.sh
docker system prune -f
```

### Support Contacts
- **Infrastructure Issues**: Pranit
- **Application Issues**: Development Team
- **Documentation**: Check `docs/` directory

---

## ✨ Tips for Success

### Development Best Practices
1. **Always test locally** before merging to prod
2. **Use the helper scripts** instead of manual Docker commands
3. **Check logs regularly** to catch issues early
4. **Keep dependencies updated** in requirements.dev.txt
5. **Write tests** for new features

### Git Workflow
```bash
# Good practice
git checkout prod-dev
git pull origin prod-dev
# Make changes
./scripts/dev-test.sh  # Always test!
git add .
git commit -m "descriptive message"
git push origin prod-dev

# When ready for production
git checkout prod
git merge prod-dev
git push origin prod
```

---

## 🎉 You're Ready!

Your local development environment is now set up with:
- ✅ **PostgreSQL database** with sample data
- ✅ **Redis caching** for performance  
- ✅ **Auto-reloading API** for fast development
- ✅ **Background worker** for async tasks
- ✅ **Testing suite** ready to run
- ✅ **Helper scripts** for common tasks
- ✅ **AWS simulation** with LocalStack

**Happy coding!** 🚀

---

*Development Guide v1.0 | Updated: Oct 4, 2025 | Environment: prod-dev branch*
