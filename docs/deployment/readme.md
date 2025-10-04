# Deployment Documentation

Complete guides for deploying AccuNode to various environments including production and development.

## 📋 Documentation Overview

This section provides deployment guides, CI/CD configuration, and operational procedures.

## 📚 Available Documents

### Deployment Guides
- **[Production Deployment](./production-deployment.md)** - Complete production deployment guide with infrastructure setup
- **[CI/CD Pipeline](./cicd-pipeline.md)** - GitHub Actions deployment configuration (current: prod only)
- **[Environment Configuration](./environment-configuration.md)** - Environment variables and secrets management
- **[Rollback Procedures](./rollback-procedures.md)** - Emergency rollback and recovery procedures

## 🌍 Environment Overview

### Development Environment
- Purpose: Local development and testing (Docker Compose)
- Database: PostgreSQL container
- Cache/Queue: Redis container
- Deployment: Manual via Docker

### Staging Environment
- Note: Not auto-deployed by CI in current workflow. Add a staging job if needed.

### Production Environment
- Purpose: Live application (AWS ECS Fargate)
- Deployment: Auto-deploy on pushes to `prod`

## 🔄 Deployment Workflow

### 1. Feature Development
```bash
# Developer workflow
git checkout prod-dev
git pull origin prod-dev
git checkout -b feature/new-ml-model
```

### 2. Production Promotion
```bash
# Merge to prod
git checkout prod
git merge prod-dev
git push origin prod
```

---

For detailed steps, see the documents above.
