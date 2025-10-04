# 📚 AccuNode Documentation Index

Welcome to the AccuNode project documentation! This guide helps you navigate all our documentation efficiently.

---

## 🚀 **Quick Start**

### **🔥 For New Developers (Local Setup)**
**Start here:** [🚀 Local Development Guide](LOCAL_DEVELOPMENT_GUIDE.md)

Complete Docker-based local development setup for the `prod-dev` branch.

### **👥 For New Team Members (AWS Access)**  
**Start here:** [📋 Team Onboarding Guide](team/TEAM_ONBOARDING_GUIDE.md)

Complete setup guide for AWS infrastructure access and team operations.

---

## 📁 **Documentation Structure**

### � **Development Documentation**
Core development guides and workflows:

- **[🚀 Local Development Guide](LOCAL_DEVELOPMENT_GUIDE.md)** - Docker-based local development setup (`prod-dev` branch)
- **[🔄 Development Workflow](DEVELOPMENT_WORKFLOW.md)** - Complete dev workflow: `prod-dev` → `prod` → AWS deployment
- **[📋 Documentation Summary](team/DOCUMENTATION_SUMMARY.md)** - Overview of all documentation organization

### �👥 **Team Documentation** (`/docs/team/`)
Essential guides for all team members:

- **[📋 Team Onboarding Guide](team/TEAM_ONBOARDING_GUIDE.md)** - Complete setup guide for new team members  
- **[🚀 Quick Reference](team/QUICK_REFERENCE.md)** - Essential commands and daily operations

### 🏗️ **AWS Infrastructure** (`/docs/aws/`)

#### **Infrastructure (`/aws/infrastructure/`)**
- **[📊 Complete Infrastructure Guide](aws/infrastructure/COMPLETE_INFRASTRUCTURE_GUIDE.md)** - Detailed overview of all AWS services
- **[💰 Cost Optimization Guide](aws/infrastructure/COST_OPTIMIZATION_GUIDE.md)** - Cost analysis and optimization strategies

#### **Deployment (`/aws/deployment/`)**  
- **[🚀 CI/CD Setup](aws/deployment/CI_CD_SETUP.md)** - GitHub Actions pipeline configuration
- **[🔄 Rollback Plan](aws/deployment/ROLLBACK_PLAN.md)** - Emergency rollback procedures
- **[📋 AWS Deployment Plan](aws/deployment/AWS_DEPLOYMENT_PLAN.md)** - Infrastructure deployment strategy
- **[✅ Deployment Ready](aws/deployment/DEPLOYMENT_READY.md)** - Pre-deployment checklist
- **[⚡ GitHub Actions Optimization](aws/deployment/GITHUB_ACTIONS_OPTIMIZATION.md)** - Pipeline optimizations

#### **Database (`/aws/database/`)**
- **[🗄️ Complete Database Access Guide](aws/database/COMPLETE_DATABASE_ACCESS_GUIDE.md)** - Comprehensive database access instructions
- **[🚀 Database Connection Helper](aws/database/connect-database.sh)** - Automated connection script
- **[📝 RDS Access Setup](aws/database/RDS_ACCESS_SETUP.md)** - Database connection procedures
- **[🖥️ EC2 Bastion Setup](aws/database/EC2_BASTION_SETUP.md)** - Bastion host configuration
- **[📊 EC2 Database Setup](aws/database/EC2_DATABASE_SETUP.md)** - Database server setup
- **[🔗 ECS Database Access](aws/database/ECS_DATABASE_ACCESS.md)** - Container database connections
- **[🌐 Make RDS Public](aws/database/MAKE_RDS_PUBLIC.md)** - Public database access (not recommended for prod)
- **[📝 Connect RDS Script](aws/database/connect-rds.sh)** - Database connection script

#### **Security (`/aws/security/`)**
- **[🔒 Critical Security Audit](aws/security/CRITICAL_SECURITY_AUDIT.md)** - Security assessment
- **[✅ Final Security Audit](aws/security/FINAL_SECURITY_AUDIT_PRODUCTION_READY.md)** - Production security validation
- **[🛡️ Security Fixes Complete](aws/security/SECURITY_FIXES_COMPLETE.md)** - Applied security patches
- **[🔐 Updated Security Audit 2025](aws/security/UPDATED_SECURITY_AUDIT_2025.md)** - Latest security review
- **[📋 Lambda VPC Policy](aws/security/lambda-vpc-policy.json)** - Lambda networking policy
- **[🔑 SSM Parameter Policy](aws/security/ssm-parameter-policy.json)** - Parameter Store permissions

### **📱 Application Documentation** (`/docs/application/`)
- **[🔗 API Register Endpoint](application/API_REGISTER_ENDPOINT.md)** - User registration API details
- **[📊 Bulk Upload API Changes](application/BULK_UPLOAD_API_CHANGES.md)** - Bulk data upload functionality
- **[👑 Create Super Admin Instructions](application/CREATE_SUPER_ADMIN_INSTRUCTIONS.md)** - Admin user setup
- **[✅ Codebase Validation](application/CODEBASE_VALIDATION.md)** - Code quality checks

### **⚙️ Operations Documentation** (`/docs/operations/`)
- **[🔧 CI/CD Fix Summary](operations/CI_CD_FIX_SUMMARY.md)** - Pipeline troubleshooting
- **[📋 Final Fix Summary](operations/FINAL_FIX_SUMMARY.md)** - Production issue resolutions
- **[☁️ CloudShell Instructions](operations/CLOUDSHELL_INSTRUCTIONS.md)** - AWS CloudShell usage

---

## 🎯 **Common Use Cases**

### **🆕 New Team Member**
1. Start with [Team Onboarding Guide](team/TEAM_ONBOARDING_GUIDE.md)
2. Set up local environment
3. Get AWS access
4. Review [Quick Reference](team/QUICK_REFERENCE.md)

### **🚀 Deploying Code**
1. Check [CI/CD Setup](aws/deployment/CI_CD_SETUP.md)
2. Push to `prod` branch
3. Monitor deployment
4. Use [Rollback Plan](aws/deployment/ROLLBACK_PLAN.md) if needed

### **🗄️ Database Access**
1. Read [Complete Database Access Guide](aws/database/COMPLETE_DATABASE_ACCESS_GUIDE.md)
2. Use [Database Connection Helper](aws/database/connect-database.sh)
3. Follow [RDS Access Setup](aws/database/RDS_ACCESS_SETUP.md) for detailed setup

### **💰 Cost Management**
1. Review [Cost Optimization Guide](aws/infrastructure/COST_OPTIMIZATION_GUIDE.md)
2. Monitor AWS billing dashboard
3. Implement suggested optimizations

### **🛠️ Infrastructure Changes**
1. Consult [Complete Infrastructure Guide](aws/infrastructure/COMPLETE_INFRASTRUCTURE_GUIDE.md)
2. Follow security guidelines
3. Update documentation

### **🚨 Emergency Issues**
1. Check [Quick Reference](team/QUICK_REFERENCE.md) for common fixes
2. Use [Rollback Plan](aws/deployment/ROLLBACK_PLAN.md) for deployments
3. Contact infrastructure owner

---

## 📊 **Project Overview**

### **Key Information**
- **AWS Account**: `461962182774`
- **Project Owner**: Pranit 
- **GitHub**: `betterresumes/default-rate-backend`
- **Production Branch**: `prod`
- **Monthly Cost**: ~$108 USD

### **Architecture**
```
Internet → ALB → ECS Fargate → RDS PostgreSQL
                     ↓
               ElastiCache Redis
                     ↓
             Parameter Store (Secrets)
```

### **Services**
- **🖥️ ECS Fargate**: Auto-scaling containers (API + Worker)
- **🗄️ RDS PostgreSQL**: Primary database
- **⚡ ElastiCache Redis**: Caching layer  
- **🌐 ALB**: Load balancing
- **🔐 Parameter Store**: Secret management
- **📦 ECR**: Container registry

---

## 🔧 **Quick Commands**

### **Service Status**
```bash
aws ecs describe-services --cluster AccuNode-Production --services accunode-api-service accunode-worker-service
```

### **View Logs**
```bash
aws logs tail /ecs/accunode-api --follow
```

### **Deploy**
```bash
git push origin prod  # Automatic CI/CD
```

### **Scale**
```bash
aws ecs update-service --cluster AccuNode-Production --service accunode-api-service --desired-count 2
```

### **Database**
```bash
ssh -i bastion-access-key.pem ec2-user@<BASTION_IP>
psql -h accunode-postgres.xxxxx.us-east-1.rds.amazonaws.com -U admin -d accunode_production
```

---

## 📞 **Support & Contacts**

### **Primary Contact**
- **Infrastructure Owner**: Pranit
- **Email**: pranit@company.com  
- **AWS Account**: 461962182774

### **Resources**
- **AWS Console**: [ECS Dashboard](https://console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/AccuNode-Production)
- **GitHub**: [Actions](https://github.com/betterresumes/default-rate-backend/actions)
- **Costs**: [AWS Billing](https://console.aws.amazon.com/billing/home#/)

### **Emergency Procedures**
1. Check service status in AWS Console
2. Review recent GitHub Actions
3. Contact infrastructure owner
4. Use rollback procedures if needed

---

## 🔄 **Recent Updates**

- **Oct 4, 2025**: Complete documentation reorganization
- **Oct 4, 2025**: Auto-scaling limits updated (max 4 containers)
- **Oct 2025**: Production infrastructure deployment complete
- **Oct 2025**: CI/CD pipeline implemented

---

## 📈 **Next Steps**

### **Planned Improvements**
- Multi-AZ database deployment
- Enhanced monitoring dashboards
- Cost optimization implementation
- Team access automation

### **Contributing to Documentation**
1. Keep documentation updated with changes
2. Add troubleshooting tips based on experience
3. Improve onboarding process
4. Share feedback on documentation structure

---

*Documentation Index v1.0 | Updated: Oct 4, 2025 | Owner: AccuNode Team*

**Need help? Start with the [Team Onboarding Guide](team/TEAM_ONBOARDING_GUIDE.md)! 🚀**
