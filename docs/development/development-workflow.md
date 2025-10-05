# Development Workflow

Complete guide for the AccuNode development process, Git workflow, and collaboration guidelines.


## Branch Strategy

### Branch Structure

```

── prod (production deployment)
│   ├── prod-dev (active development)
└── develop (integration branch)
```

### Branch Descriptions

| Branch | Purpose | Deployment | Protection |
|--------|---------|------------|------------|
| **** | Production-ready code | Manual to AWS | Protected, PR required |
| **prod** | Current production | Auto-deploy to AWS | Protected, PR required |
| **prod-dev** | Active development | Auto-deploy to staging | Protected, PR required |


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