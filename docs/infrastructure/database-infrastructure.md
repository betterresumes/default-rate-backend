# 🗄️ Database Infrastructure Documentation

## 📋 **Table of Contents**
1. [Database Infrastructure Overview](#database-infrastructure-overview)
2. [RDS PostgreSQL Setup](#rds-postgresql-setup)
3. [ElastiCache Redis Configuration](#elasticache-redis-configuration)
4. [Database Security & Access](#database-security--access)
5. [Backup & Recovery Strategy](#backup--recovery-strategy)
6. [Monitoring & Performance](#monitoring--performance)
7. [Database Maintenance](#database-maintenance)
8. [Scaling & Optimization](#scaling--optimization)
9. [Disaster Recovery](#disaster-recovery)
10. [Troubleshooting](#troubleshooting)

---

## 🏗️ **Database Infrastructure Overview**

AccuNode uses a dual-database architecture with PostgreSQL for persistent data and Redis for caching, sessions, and task queues in a high-availability AWS setup.

### **Architecture Components**

```
┌─────────────────────────────────────────────────────────┐
│                    ECS Fargate Tasks                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   API       │  │   Worker    │  │   Celery    │    │
│  │  Service    │  │   Service   │  │   Beat      │    │
│  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────┘
           │                    │                │
           ▼                    ▼                ▼
┌─────────────────┐    ┌─────────────────────────────────┐
│  RDS PostgreSQL │    │      ElastiCache Redis          │
│                 │    │                                 │
│ • Primary Data  │    │ • Session Store                 │
│ • single-AZ      │    │ • Cache Layer                   │
│ • Read Replicas │    │ • Task Queue (Celery)          │
│ • Automated     │    │ • Rate Limiting                 │
│   Backups       │    │ • Cluster Mode                  │
└─────────────────┘    └─────────────────────────────────┘
```