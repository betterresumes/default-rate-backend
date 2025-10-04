# Infrastructure Documentation

Complete AWS infrastructure setup and configuration guides for AccuNode.

## 📋 Documentation Overview

This section provides comprehensive guides for deploying, configuring, and managing the AWS infrastructure that powers AccuNode.

## 📚 Available Documents

### Core Infrastructure
- **[ECS Fargate Setup](./ecs-fargate-setup.md)** - Complete container orchestration setup with AWS Fargate
- **[Database Infrastructure](./database-infrastructure.md)** - AWS RDS PostgreSQL configuration and management
- **[Load Balancer Setup](./load-balancer-setup.md)** - Application Load Balancer configuration and SSL termination
- **[Security Groups](./security-groups.md)** - Network security configuration and traffic rules

## 🏗️ Infrastructure Architecture

```
Internet Gateway
       │
       ▼
┌─────────────────┐     ┌─────────────────┐
│  Public Subnet  │     │  Public Subnet  │
│   (us-east-1a)  │     │   (us-east-1b)  │
│                 │     │                 │
│ ┌─────────────┐ │     │ ┌─────────────┐ │
│ │     ALB     │ │     │ │   Bastion   │ │
│ │             │ │     │ │    Host     │ │
│ └─────────────┘ │     │ └─────────────┘ │
└─────────────────┘     └─────────────────┘
       │                         │
       ▼                         ▼
┌─────────────────┐     ┌─────────────────┐
│ Private Subnet  │     │ Private Subnet  │
│  (us-east-1a)   │     │  (us-east-1b)   │
│                 │     │                 │
│ ┌─────────────┐ │     │ ┌─────────────┐ │
│ │ ECS Fargate │ │     │ │ ECS Fargate │ │
│ │   Tasks     │ │     │ │   Tasks     │ │
│ └─────────────┘ │     │ └─────────────┘ │
│                 │     │                 │
│ ┌─────────────┐ │     │ ┌─────────────┐ │
│ │     RDS     │ │     │ │   Redis     │ │
│ │ PostgreSQL  │ │     │ │ElastiCache  │ │
│ └─────────────┘ │     │ └─────────────┘ │
└─────────────────┘     └─────────────────┘
```

## ☁️ AWS Services Used

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **VPC** | Network isolation | 10.0.0.0/16 CIDR |
| **ECS Fargate** | Container orchestration | Auto-scaling 2-10 tasks |
| **RDS PostgreSQL** | Primary database | Multi-AZ, encrypted |
| **ElastiCache Redis** | Caching and sessions | Single node, encrypted |
| **Application Load Balancer** | Load balancing & SSL | Internet-facing, HTTPS |
| **Route53** | DNS management | api.accunode.com |
| **Certificate Manager** | SSL certificates | Wildcard cert |
| **CloudWatch** | Monitoring & logging | Metrics and log aggregation |
| **Parameter Store** | Configuration management | Encrypted secrets |

## 🚀 Quick Setup Guide

### Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform v1.5+ for infrastructure as code
- Domain name registered and managed in Route53

### 1. Network Foundation
```bash
# Deploy VPC and networking
terraform apply -target=module.vpc
```

### 2. Security Configuration  
```bash
# Deploy security groups
terraform apply -target=module.security_groups
```

### 3. Database Layer
```bash
# Deploy RDS and Redis
terraform apply -target=module.rds
terraform apply -target=module.redis
```

### 4. Application Layer
```bash
# Deploy ECS cluster and load balancer
terraform apply -target=module.ecs
terraform apply -target=module.alb
```

### 5. DNS and SSL
```bash
# Configure domain and certificates
terraform apply -target=module.route53
terraform apply -target=module.acm
```

## 🔧 Configuration Management

### Environment Variables

AccuNode uses AWS Parameter Store for configuration management:

```bash
# Database configuration
/accunode/production/database/host
/accunode/production/database/name
/accunode/production/database/username
/accunode/production/database/password

# Redis configuration
/accunode/production/redis/host
/accunode/production/redis/port

# Application secrets
/accunode/production/jwt/secret
/accunode/production/app/environment
```

### Security Configuration

All infrastructure follows AWS security best practices:

- **Network Security**: VPC with public/private subnets
- **Access Control**: IAM roles with least privilege
- **Data Encryption**: Encryption at rest and in transit
- **Monitoring**: CloudWatch logs and metrics
- **Backup**: Automated RDS backups with 7-day retention

## 📊 Resource Specifications

### Production Environment

| Resource Type | Instance Type | Capacity | Notes |
|---------------|---------------|----------|-------|
| **ECS Tasks** | 512 CPU / 1024 MB | 2-10 tasks | Auto-scaling enabled |
| **RDS PostgreSQL** | db.t3.medium | 100GB SSD | Multi-AZ deployment |
| **ElastiCache Redis** | cache.t3.micro | 1 node | Single AZ (non-critical) |
| **Application Load Balancer** | Standard | 2 AZ | Cross-zone load balancing |

### Staging Environment

| Resource Type | Instance Type | Capacity | Notes |
|---------------|---------------|----------|-------|
| **ECS Tasks** | 256 CPU / 512 MB | 1-3 tasks | Lower capacity for testing |
| **RDS PostgreSQL** | db.t3.small | 20GB SSD | Single AZ deployment |
| **ElastiCache Redis** | cache.t3.nano | 1 node | Minimal configuration |

## 🔐 Security Features

### Network Security
- **VPC Isolation**: Dedicated VPC with controlled access
- **Private Subnets**: Database and application tiers isolated
- **Security Groups**: Minimal required access rules
- **NACLs**: Additional network-level filtering

### Data Security
- **Encryption at Rest**: RDS and EBS volumes encrypted
- **Encryption in Transit**: TLS/SSL for all connections
- **Secrets Management**: AWS Parameter Store with KMS
- **Backup Encryption**: Automated encrypted backups

### Access Security
- **IAM Roles**: Service-specific roles with minimal permissions
- **MFA Required**: Multi-factor authentication for admin access
- **Audit Logging**: CloudTrail for all API calls
- **VPC Flow Logs**: Network traffic monitoring

## 📈 Monitoring & Alerts

### CloudWatch Metrics
- ECS task CPU and memory utilization
- RDS connection count and query performance
- ALB request count and response times
- ElastiCache hit rates and memory usage

### Alerting Thresholds
- High error rate: >5% 5xx responses
- High latency: >2 second response times
- Resource exhaustion: >80% CPU/memory
- Database issues: >100 active connections

### Log Aggregation
- Application logs: `/aws/ecs/accunode-api`
- Load balancer logs: S3 bucket storage
- VPC Flow Logs: CloudWatch Logs
- Database logs: RDS log files

## 💰 Cost Optimization

### Current Monthly Costs (Production)

| Service | Monthly Cost | Optimization Notes |
|---------|--------------|-------------------|
| **ECS Fargate** | ~$45 | Right-sized containers |
| **RDS PostgreSQL** | ~$65 | Reserved instance available |
| **ElastiCache** | ~$15 | Minimal instance size |
| **Load Balancer** | ~$25 | Standard ALB pricing |
| **Data Transfer** | ~$10 | Optimize with CloudFront |
| **Total** | **~$160/month** | 20% savings with reserved instances |

### Cost Optimization Strategies
- Use Reserved Instances for predictable workloads
- Implement auto-scaling to reduce over-provisioning
- Monitor and optimize data transfer costs
- Regular review of unused resources

## 🔗 Related Documentation

- **[Production Deployment](../deployment/production-deployment.md)** - Complete deployment procedures
- **[Common Issues](../troubleshooting/common-issues.md)** - Infrastructure troubleshooting
- **[System Architecture](../core-application/system-architecture.md)** - Application architecture overview

## 📞 Support

For infrastructure-related issues:
1. Review the specific component documentation above
2. Check AWS service health dashboards
3. Review CloudWatch metrics and logs
4. Contact AWS Support for service-level issues
5. Escalate to infrastructure team for complex issues

---

*Last Updated: October 2025 | AccuNode Infrastructure Team*
