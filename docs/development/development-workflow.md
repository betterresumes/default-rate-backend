# Development Workflow

Complete guide for the AccuNode development process, Git workflow, and collaboration guidelines.

## Overview

AccuNode follows a structured development workflow to ensure code quality, maintain stability, and enable smooth deployments to production.

## Branch Strategy

### Branch Structure

```
main (production-ready)
├── prod (production deployment)
│   ├── prod-dev (active development)
│   │   ├── feature/ml-improvements
│   │   ├── feature/api-enhancements  
│   │   ├── bugfix/auth-validation
│   │   └── hotfix/security-patch
│   └── release/v2.1.0
└── develop (integration branch)
```

### Branch Descriptions

| Branch | Purpose | Deployment | Protection |
|--------|---------|------------|------------|
| **main** | Production-ready code | Manual to AWS | Protected, PR required |
| **prod** | Current production | Auto-deploy to AWS | Protected, PR required |
| **prod-dev** | Active development | Auto-deploy to staging | Protected, PR required |
| **feature/** | New features | Local/dev environments | None |
| **bugfix/** | Bug fixes | Local/dev environments | None |
| **hotfix/** | Emergency fixes | Direct to prod | Expedited review |
| **release/** | Version preparation | Staging environment | Protected |

## Development Workflow

### 1. Starting New Work

```bash
# Update local repository
git checkout prod-dev
git pull origin prod-dev

# Create feature branch
git checkout -b feature/prediction-improvements
```

### 2. Development Process

```bash
# Make changes and commit frequently
git add .
git commit -m "feat: add quarterly prediction confidence scoring"

# Push feature branch
git push origin feature/prediction-improvements
```

### 3. Code Review Process

```bash
# Create Pull Request to prod-dev
# PR Title: "feat: Add quarterly prediction confidence scoring"
# PR Description should include:
# - What changes were made
# - Why the changes were needed  
# - How to test the changes
# - Any breaking changes or migrations needed
```

### 4. Merging Process

```bash
# After PR approval, squash and merge
git checkout prod-dev
git pull origin prod-dev

# Feature branch is automatically deleted after merge
```

## Commit Message Convention

### Format

```
type(scope): description

[optional body]

[optional footer]
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| **feat** | New feature | `feat(api): add bulk upload endpoint` |
| **fix** | Bug fix | `fix(auth): resolve JWT token validation` |
| **docs** | Documentation | `docs(api): update prediction API examples` |
| **style** | Formatting | `style(core): fix code formatting` |
| **refactor** | Code restructuring | `refactor(ml): improve model loading performance` |
| **test** | Testing | `test(api): add integration tests for predictions` |
| **chore** | Build/tooling | `chore(deps): upgrade FastAPI to 0.104.1` |

### Examples

```bash
# Feature addition
git commit -m "feat(predictions): add quarterly ensemble model support"

# Bug fix
git commit -m "fix(auth): handle expired JWT tokens gracefully"

# Documentation update
git commit -m "docs(deployment): add production deployment guide"

# Breaking change
git commit -m "feat(api)!: change prediction response format

BREAKING CHANGE: prediction response now includes confidence scores"
```

## Code Quality Standards

### 1. Python Code Style

```python
# Use Black formatter (automatic)
black .

# Use isort for imports (automatic)
isort .

# Use flake8 for linting
flake8 app/ tests/

# Use mypy for type checking
mypy app/
```

### 2. Code Quality Checklist

Before submitting a PR, ensure:

- [ ] Code follows PEP 8 style guidelines
- [ ] All functions have type hints
- [ ] Docstrings are provided for public functions
- [ ] Unit tests cover new functionality
- [ ] Integration tests pass
- [ ] No security vulnerabilities introduced
- [ ] Performance impact is acceptable
- [ ] Breaking changes are documented

### 3. Pre-commit Hooks

Install pre-commit hooks to ensure code quality:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Configuration in .pre-commit-config.yaml:
repos:
  - repo: https://github.com/psf/black
    rev: 23.9.1
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.0
    hooks:
      - id: mypy
```

## Testing Strategy

### 1. Test Types

| Test Type | Purpose | Command | Coverage |
|-----------|---------|---------|----------|
| **Unit Tests** | Individual function testing | `pytest tests/unit/` | Business logic |
| **Integration Tests** | API endpoint testing | `pytest tests/integration/` | API contracts |
| **E2E Tests** | Full workflow testing | `pytest tests/e2e/` | User scenarios |
| **Performance Tests** | Load and stress testing | `locust -f tests/performance/` | System limits |

### 2. Test Requirements

All PRs must include:

- Unit tests for new functions (minimum 80% coverage)
- Integration tests for new API endpoints
- Documentation updates for API changes
- Performance tests for ML model changes

### 3. Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest -k "test_prediction"

# Run performance tests
locust -f tests/performance/load_test.py --host=http://localhost:8000
```

## CI/CD Pipeline

### 1. GitHub Actions Workflow

```yaml
# .github/workflows/ci-cd.yml (current)
name: CI/CD Pipeline - AccuNode Production

on:
  push:
    branches: [prod]
  pull_request:
    branches: [prod]
```

- Current behavior: deploys on pushes to `prod`. Staging auto-deploy is not configured.
- If staging is needed, add a separate workflow on `prod-dev`.

### 2. Deployment Triggers

| Branch | Trigger | Target | Auto-deploy |
|--------|---------|--------|-------------|
| **prod-dev** | Manual/PR review | Staging (optional) | ❌ Not configured |
| **prod** | Push/merge | Production | ✅ Yes |
| **main** | Manual | Production (backup) | ❌ Manual |

## Local Development Setup

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/accunodeai/server.git
cd server

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.dev.txt
```

### 2. Docker Development Environment

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up -d

# View logs (service name is 'api')
docker-compose -f docker-compose.dev.yml logs -f api

# Run tests in container
docker-compose -f docker-compose.dev.yml exec api pytest
```

### 3. Environment Variables

Create `.env.local` (or use `.env.development`):

```bash
# Direct DATABASE_URL is preferred by the app
DATABASE_URL=postgresql://admin:dev_password_123@localhost:5432/accunode_development

# Redis
REDIS_URL=redis://default:dev_redis_password@localhost:6379

# JWT
JWT_SECRET_KEY=dev-secret-key-change-in-production
JWT_ALGORITHM=HS256

# App
ENVIRONMENT=development
DEBUG=true
```

Notes
- `docker-compose.dev.yml` sets matching values inside containers; use localhost values when accessing from host.
- Alembic migrations are not required; SQLAlchemy creates tables on startup. Remove Alembic steps if not configured.

## Documentation Standards

### 1. Code Documentation

```python
def predict_default_risk(
    financial_ratios: Dict[str, float],
    model_type: str = "annual"
) -> PredictionResult:
    """
    Predict default risk using ML models.
    
    Args:
        financial_ratios: Dictionary of financial ratio names and values
        model_type: Type of model to use ("annual" or "quarterly")
    
    Returns:
        PredictionResult containing probability, risk level, and confidence
        
    Raises:
        ValidationError: If financial ratios are invalid
        ModelError: If ML model prediction fails
        
    Example:
        >>> ratios = {"debt_to_equity": 0.5, "current_ratio": 2.1}
        >>> result = predict_default_risk(ratios, "annual")
        >>> print(result.risk_level)
        "Low Risk"
    """
```

### 2. API Documentation

- All API changes must update OpenAPI specifications
- Include request/response examples
- Document error responses and status codes
- Provide integration examples

### 3. Architecture Documentation

- Update system architecture diagrams for major changes
- Document database schema changes
- Explain ML model updates and performance impacts
- Maintain deployment guides

## Performance Monitoring

### 1. Development Metrics

Monitor during development:

- Response time < 200ms for API endpoints
- Memory usage < 512MB per container
- CPU usage < 70% under normal load
- Database query time < 50ms average

### 2. Performance Testing

```bash
# API load testing
locust -f tests/performance/api_load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10
```

## Security Guidelines

### 1. Security Checklist

- [ ] Input validation on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS protection (input sanitization)
- [ ] Authentication required for all non-public endpoints
- [ ] Authorization checks for data access
- [ ] Secrets not committed to repository
- [ ] Dependencies scanned for vulnerabilities

### 2. Security Tools

```bash
# Dependency vulnerability scanning
safety check

# Code security scanning
bandit -r app/

# Secrets scanning
truffleHog --git https://github.com/accunodeai/server.git
```

---

*For additional development support, refer to the [Local Setup Guide](./local-setup.md) and [Testing Guide](./testing-guide.md).*
