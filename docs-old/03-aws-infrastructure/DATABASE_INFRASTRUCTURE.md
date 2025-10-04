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
│ • Multi-AZ      │    │ • Cache Layer                   │
│ • Read Replicas │    │ • Task Queue (Celery)          │
│ • Automated     │    │ • Rate Limiting                 │
│   Backups       │    │ • Cluster Mode                  │
└─────────────────┘    └─────────────────────────────────┘
```

### **Database Roles & Responsibilities**

| Database | Purpose | Data Types | Persistence |
|----------|---------|------------|-------------|
| **PostgreSQL** | Primary database | Users, Companies, Predictions, Organizations | Persistent |
| **Redis** | Cache & queue | Sessions, Cache, Tasks, Rate limits | Temporary |

---

## 🐘 **RDS PostgreSQL Setup**

### **Instance Configuration**

**Production Environment:**
```yaml
DBInstanceIdentifier: accunode-db-prod
DBInstanceClass: db.r6g.xlarge  # 4 vCPU, 32 GB RAM
Engine: postgres
EngineVersion: '15.4'
AllocatedStorage: 500  # GB
StorageType: gp3
StorageEncrypted: true
KmsKeyId: arn:aws:kms:us-east-1:ACCOUNT:key/KMS-KEY-ID

# Multi-AZ for high availability
MultiAZ: true
AvailabilityZone: us-east-1a
SecondaryAvailabilityZone: us-east-1b

# Network & Security
DBSubnetGroupName: accunode-db-subnet-group-prod
VpcSecurityGroupIds:
  - sg-rds-accunode-prod
Port: 5432
PubliclyAccessible: false

# Backup & Maintenance
BackupRetentionPeriod: 30  # days
BackupWindow: "03:00-04:00"  # UTC
MaintenanceWindow: "sun:04:00-sun:05:00"  # UTC
DeletionProtection: true
```

**Development Environment:**
```yaml
DBInstanceIdentifier: accunode-db-dev
DBInstanceClass: db.t3.medium  # 2 vCPU, 4 GB RAM
Engine: postgres
EngineVersion: '15.4'
AllocatedStorage: 100  # GB
StorageType: gp3
MultiAZ: false
BackupRetentionPeriod: 7  # days
DeletionProtection: false
```

### **Database Parameters**

**Custom Parameter Group:**
```yaml
ParameterGroupName: accunode-postgres-params-prod
Family: postgres15
Parameters:
  # Performance Optimization
  shared_preload_libraries: 'pg_stat_statements'
  max_connections: 200
  shared_buffers: '8GB'  # 25% of RAM for r6g.xlarge
  effective_cache_size: '24GB'  # 75% of RAM
  maintenance_work_mem: '2GB'
  work_mem: '64MB'
  
  # Query Performance
  random_page_cost: 1.1  # For SSD storage
  effective_io_concurrency: 200
  max_worker_processes: 8
  max_parallel_workers_per_gather: 4
  max_parallel_workers: 8
  
  # Write Ahead Log (WAL)
  wal_buffers: '16MB'
  checkpoint_completion_target: 0.9
  checkpoint_timeout: '10min'
  max_wal_size: '4GB'
  min_wal_size: '1GB'
  
  # Logging & Monitoring
  log_statement: 'mod'  # Log all DDL/DML
  log_min_duration_statement: 1000  # Log queries > 1 second
  log_checkpoints: 'on'
  log_connections: 'on'
  log_disconnections: 'on'
  log_lock_waits: 'on'
  
  # Security
  ssl: 'on'
  password_encryption: 'scram-sha-256'
  
  # Extensions
  shared_preload_libraries: 'pg_stat_statements,pg_cron'
```

### **Database Schema Structure**

**Core Tables:**
```sql
-- Tenants (multi-tenancy)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    domain VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_organizations_tenant_id ON organizations(tenant_id);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID REFERENCES tenants(id),
    organization_id UUID REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_tenant_org ON users(tenant_id, organization_id);

-- Companies
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id),
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    market_cap BIGINT,
    sector VARCHAR(100),
    country VARCHAR(100),
    exchange VARCHAR(50),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_companies_symbol ON companies(symbol);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_org ON companies(organization_id);

-- Annual Predictions
CREATE TABLE annual_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    created_by UUID REFERENCES users(id),
    reporting_year VARCHAR(4) NOT NULL,
    
    -- Financial Ratios
    long_term_debt_to_total_capital DECIMAL(10,6),
    total_debt_to_ebitda DECIMAL(10,6),
    net_income_margin DECIMAL(10,6),
    ebit_to_interest_expense DECIMAL(10,6),
    return_on_assets DECIMAL(10,6),
    
    -- Prediction Results
    probability DECIMAL(10,6) NOT NULL,
    risk_level VARCHAR(10) NOT NULL,
    confidence DECIMAL(10,6),
    
    -- Model Details
    logistic_probability DECIMAL(10,6),
    step_probability DECIMAL(10,6),
    
    access_level VARCHAR(20) DEFAULT 'personal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(company_id, reporting_year)
);
CREATE INDEX idx_annual_predictions_company ON annual_predictions(company_id);
CREATE INDEX idx_annual_predictions_year ON annual_predictions(reporting_year);
CREATE INDEX idx_annual_predictions_risk ON annual_predictions(risk_level);

-- Quarterly Predictions  
CREATE TABLE quarterly_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID REFERENCES companies(id),
    created_by UUID REFERENCES users(id),
    reporting_year VARCHAR(4) NOT NULL,
    reporting_quarter VARCHAR(2) NOT NULL,
    
    -- Financial Ratios
    current_ratio DECIMAL(10,6),
    quick_ratio DECIMAL(10,6),
    debt_to_equity DECIMAL(10,6),
    inventory_turnover DECIMAL(10,6),
    receivables_turnover DECIMAL(10,6),
    working_capital_to_total_assets DECIMAL(10,6),
    
    -- Prediction Results
    ensemble_probability DECIMAL(10,6) NOT NULL,
    logistic_probability DECIMAL(10,6),
    gbm_probability DECIMAL(10,6),
    step_probability DECIMAL(10,6),
    risk_level VARCHAR(10) NOT NULL,
    confidence DECIMAL(10,6),
    
    access_level VARCHAR(20) DEFAULT 'personal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(company_id, reporting_year, reporting_quarter)
);
CREATE INDEX idx_quarterly_predictions_company ON quarterly_predictions(company_id);
CREATE INDEX idx_quarterly_predictions_period ON quarterly_predictions(reporting_year, reporting_quarter);
```

### **Read Replicas Configuration**

```yaml
# Read Replica for Analytics Queries
ReadReplica1:
  DBInstanceIdentifier: accunode-db-replica-analytics
  SourceDBInstanceIdentifier: accunode-db-prod
  DBInstanceClass: db.r6g.large  # Smaller instance for read queries
  AvailabilityZone: us-east-1c
  PubliclyAccessible: false
  
# Read Replica for Reporting
ReadReplica2:
  DBInstanceIdentifier: accunode-db-replica-reports
  SourceDBInstanceIdentifier: accunode-db-prod  
  DBInstanceClass: db.r6g.large
  AvailabilityZone: us-east-1d
  PubliclyAccessible: false
```

---

## 🔴 **ElastiCache Redis Configuration**

### **Redis Cluster Setup**

**Production Cluster:**
```yaml
ReplicationGroupId: accunode-redis-prod
Description: AccuNode Redis Cluster for Production
NodeType: cache.r6g.large  # 2 vCPU, 16.88 GB RAM
Engine: redis
EngineVersion: '7.0'
Port: 6379

# Cluster Configuration
NumCacheClusters: 3  # 1 Primary + 2 Replicas
ReplicasPerNodeGroup: 2
NumNodeGroups: 1  # Single shard initially

# Network & Security
CacheSubnetGroupName: accunode-redis-subnet-group
SecurityGroupIds:
  - sg-redis-accunode-prod
PreferredAvailabilityZones:
  - us-east-1a
  - us-east-1b
  - us-east-1c

# Backup & Maintenance
SnapshotRetentionLimit: 5  # days
SnapshotWindow: "03:00-05:00"  # UTC
PreferredMaintenanceWindow: "sun:05:00-sun:07:00"  # UTC

# Security
AtRestEncryptionEnabled: true
TransitEncryptionEnabled: true
AuthToken: !Ref RedisAuthToken  # From Secrets Manager

# Performance
CacheParameterGroupName: accunode-redis-params-prod
```

### **Redis Parameter Group**

```yaml
ParameterGroupName: accunode-redis-params-prod
Family: redis7.x
Parameters:
  # Memory Management
  maxmemory-policy: 'allkeys-lru'  # Evict least recently used keys
  timeout: 300  # Client idle timeout (5 minutes)
  tcp-keepalive: 300
  
  # Performance
  hash-max-ziplist-entries: 512
  hash-max-ziplist-value: 64
  list-max-ziplist-size: -2
  set-max-intset-entries: 512
  zset-max-ziplist-entries: 128
  zset-max-ziplist-value: 64
  
  # Persistence (disabled for cache-only usage)
  save: ''  # Disable RDB snapshots
  
  # Logging
  loglevel: 'notice'
  syslog-enabled: 'yes'
  
  # Slow Log
  slowlog-log-slower-than: 10000  # 10ms
  slowlog-max-len: 128
```

### **Redis Usage Patterns**

```python
# Redis Key Patterns and Usage
REDIS_KEY_PATTERNS = {
    # Session Management
    "session:{session_id}": {
        "ttl": 86400,  # 24 hours
        "data": "user session data"
    },
    
    # Rate Limiting
    "rate_limit:{user_id}:{endpoint}": {
        "ttl": 3600,  # 1 hour
        "data": "request count"
    },
    
    # Cache Layer
    "cache:prediction:{prediction_id}": {
        "ttl": 1800,  # 30 minutes
        "data": "prediction result"
    },
    
    "cache:company:{company_id}": {
        "ttl": 3600,  # 1 hour
        "data": "company information"
    },
    
    "cache:user:{user_id}": {
        "ttl": 900,   # 15 minutes
        "data": "user profile data"
    },
    
    # Celery Task Queue
    "celery:task:{task_id}": {
        "ttl": 86400,  # 24 hours
        "data": "task metadata"
    },
    
    # Analytics Cache
    "analytics:stats:{period}:{date}": {
        "ttl": 21600,  # 6 hours
        "data": "aggregated statistics"
    }
}
```

### **Redis Monitoring & Metrics**

```python
# Redis health monitoring
import redis
import time

def monitor_redis_health():
    r = redis.Redis(host='accunode-redis-cluster-endpoint')
    
    # Connection test
    try:
        start_time = time.time()
        r.ping()
        ping_time = (time.time() - start_time) * 1000
        print(f"Redis ping: {ping_time:.2f}ms")
    except redis.ConnectionError:
        print("Redis connection failed")
    
    # Memory usage
    info = r.info('memory')
    used_memory_mb = info['used_memory'] / (1024 * 1024)
    max_memory_mb = info['maxmemory'] / (1024 * 1024)
    memory_usage_percent = (used_memory_mb / max_memory_mb) * 100
    
    print(f"Memory usage: {used_memory_mb:.1f}MB / {max_memory_mb:.1f}MB ({memory_usage_percent:.1f}%)")
    
    # Key statistics
    total_keys = r.dbsize()
    expired_keys = info.get('expired_keys', 0)
    evicted_keys = info.get('evicted_keys', 0)
    
    print(f"Keys: {total_keys}, Expired: {expired_keys}, Evicted: {evicted_keys}")
```

---

## 🔐 **Database Security & Access**

### **Network Security**

**RDS Security Group:**
```yaml
RDSSecurityGroup:
  Type: AWS::EC2::SecurityGroup
  Properties:
    GroupName: accunode-rds-sg-prod
    GroupDescription: Security group for AccuNode RDS PostgreSQL
    VpcId: !Ref VPC
    SecurityGroupIngress:
      # PostgreSQL access from ECS tasks only
      - IpProtocol: tcp
        FromPort: 5432
        ToPort: 5432
        SourceSecurityGroupId: !Ref ECSSecurityGroup
        Description: PostgreSQL from ECS tasks
      
      # Emergency access from bastion host
      - IpProtocol: tcp
        FromPort: 5432
        ToPort: 5432
        SourceSecurityGroupId: !Ref BastionSecurityGroup
        Description: PostgreSQL from bastion host
    SecurityGroupEgress: []  # No outbound rules needed
```

**Redis Security Group:**
```yaml
RedisSecurityGroup:
  Type: AWS::EC2::SecurityGroup
  Properties:
    GroupName: accunode-redis-sg-prod
    GroupDescription: Security group for AccuNode Redis
    VpcId: !Ref VPC
    SecurityGroupIngress:
      # Redis access from ECS tasks only
      - IpProtocol: tcp
        FromPort: 6379
        ToPort: 6379
        SourceSecurityGroupId: !Ref ECSSecurityGroup
        Description: Redis from ECS tasks
    SecurityGroupEgress: []
```

### **IAM Database Authentication**

```yaml
# IAM Role for RDS access
RDSAccessRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: accunode-rds-access-role
    AssumeRolePolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            Service: ecs-tasks.amazonaws.com
          Action: sts:AssumeRole
    Policies:
      - PolicyName: RDSConnectPolicy
        PolicyDocument:
          Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - rds-db:connect
              Resource:
                - arn:aws:rds-db:us-east-1:ACCOUNT:dbuser:accunode-db-prod/app_user
```

### **Secrets Management**

```yaml
# Database credentials in Secrets Manager
DatabaseSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    Name: accunode/database/master-credentials
    Description: Master credentials for AccuNode RDS database
    GenerateSecretString:
      SecretStringTemplate: '{"username": "postgres"}'
      GenerateStringKey: 'password'
      PasswordLength: 32
      ExcludeCharacters: '"@/\'

# Application database user credentials
AppDatabaseSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    Name: accunode/database/app-credentials
    Description: Application user credentials for AccuNode database
    SecretString: !Sub |
      {
        "username": "app_user",
        "password": "${AppUserPassword}",
        "dbname": "accunode_prod",
        "host": "${DatabaseInstance.Endpoint.Address}",
        "port": ${DatabaseInstance.Endpoint.Port}
      }

# Redis auth token
RedisSecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    Name: accunode/redis/auth-token
    Description: Redis authentication token
    GenerateSecretString:
      PasswordLength: 128
      ExcludeCharacters: '"@/\'
```

### **Database Users & Permissions**

```sql
-- Create application-specific users
CREATE USER app_user WITH PASSWORD 'secure_password';
CREATE USER readonly_user WITH PASSWORD 'readonly_password';
CREATE USER analytics_user WITH PASSWORD 'analytics_password';

-- Grant appropriate permissions
GRANT CONNECT ON DATABASE accunode_prod TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Read-only user for reports
GRANT CONNECT ON DATABASE accunode_prod TO readonly_user;
GRANT USAGE ON SCHEMA public TO readonly_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- Analytics user (read-only with specific permissions)
GRANT CONNECT ON DATABASE accunode_prod TO analytics_user;
GRANT USAGE ON SCHEMA public TO analytics_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO analytics_user;

-- Row Level Security (RLS) policies
ALTER TABLE companies ENABLE ROW LEVEL SECURITY;
CREATE POLICY company_org_policy ON companies 
  FOR ALL TO app_user 
  USING (organization_id IN (
    SELECT organization_id FROM users WHERE id = current_setting('app.current_user_id')::uuid
  ));

ALTER TABLE annual_predictions ENABLE ROW LEVEL SECURITY;  
CREATE POLICY prediction_access_policy ON annual_predictions
  FOR ALL TO app_user
  USING (
    company_id IN (
      SELECT id FROM companies WHERE organization_id IN (
        SELECT organization_id FROM users WHERE id = current_setting('app.current_user_id')::uuid
      )
    )
  );
```

---

## 💾 **Backup & Recovery Strategy**

### **Automated Backup Configuration**

**RDS Automated Backups:**
```yaml
BackupConfiguration:
  BackupRetentionPeriod: 30  # days
  BackupWindow: "03:00-04:00"  # UTC, during low activity
  CopyTagsToSnapshot: true
  DeleteAutomatedBackups: false
  DeletionProtection: true
  
  # Point-in-time recovery
  PointInTimeRecoveryEnabled: true
  
  # Multi-region backup replication
  BackupReplicationRegions:
    - us-west-2
    
# Manual snapshots for major releases
ManualSnapshots:
  - SnapshotIdentifier: accunode-pre-v2-release
    Description: "Backup before v2.0 release"
    Tags:
      - Key: Purpose
        Value: pre-release-backup
      - Key: Version
        Value: v1.9.5
```

### **Redis Backup Strategy**

```yaml
RedisBackups:
  # Automatic snapshots
  SnapshotRetentionLimit: 5  # Keep 5 daily snapshots
  SnapshotWindow: "03:00-05:00"  # UTC
  
  # Manual snapshots for critical data
  FinalSnapshotIdentifier: accunode-redis-final-snapshot
  
  # Cross-region replication for disaster recovery
  GlobalReplicationGroup:
    GlobalReplicationGroupId: accunode-redis-global
    PrimaryReplicationGroupId: accunode-redis-prod
    GlobalReplicationGroupDescription: Global Redis for AccuNode
```

### **Backup Monitoring**

```python
# Monitor backup status
import boto3

def check_backup_status():
    rds = boto3.client('rds')
    
    # Check latest automated backup
    snapshots = rds.describe_db_snapshots(
        DBInstanceIdentifier='accunode-db-prod',
        SnapshotType='automated',
        MaxRecords=1
    )
    
    if snapshots['DBSnapshots']:
        latest_backup = snapshots['DBSnapshots'][0]
        backup_time = latest_backup['SnapshotCreateTime']
        status = latest_backup['Status']
        print(f"Latest backup: {backup_time}, Status: {status}")
    
    # Check point-in-time recovery window
    db_instances = rds.describe_db_instances(
        DBInstanceIdentifier='accunode-db-prod'
    )
    
    db = db_instances['DBInstances'][0]
    earliest_time = db['EarliestRestorableTime']
    latest_time = db['LatestRestorableTime']
    
    print(f"Point-in-time recovery window: {earliest_time} to {latest_time}")
```

---

## 📊 **Monitoring & Performance**

### **CloudWatch Metrics & Alarms**

**PostgreSQL Monitoring:**
```yaml
# CPU Utilization Alarm
DatabaseCPUAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: AccuNode-DB-HighCPU
    AlarmDescription: Database CPU utilization is high
    MetricName: CPUUtilization
    Namespace: AWS/RDS
    Statistic: Average
    Period: 300
    EvaluationPeriods: 2
    Threshold: 80
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: DBInstanceIdentifier
        Value: accunode-db-prod
    AlarmActions:
      - !Ref DatabaseAlarmTopic

# Connection Count Alarm
DatabaseConnectionsAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: AccuNode-DB-HighConnections
    MetricName: DatabaseConnections
    Namespace: AWS/RDS
    Threshold: 160  # 80% of max_connections (200)
    ComparisonOperator: GreaterThanThreshold

# Slow Query Monitoring
DatabaseSlowQueriesAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: AccuNode-DB-SlowQueries
    MetricName: DatabaseSlowQueries
    Namespace: AWS/RDS
    Threshold: 10
    ComparisonOperator: GreaterThanThreshold
```

**Redis Monitoring:**
```yaml
# Redis CPU Alarm
RedisCPUAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: AccuNode-Redis-HighCPU
    MetricName: CPUUtilization
    Namespace: AWS/ElastiCache
    Threshold: 75
    ComparisonOperator: GreaterThanThreshold
    Dimensions:
      - Name: CacheClusterId
        Value: accunode-redis-prod-001

# Memory Usage Alarm
RedisMemoryAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: AccuNode-Redis-HighMemory
    MetricName: DatabaseMemoryUsagePercentage
    Namespace: AWS/ElastiCache
    Threshold: 85
    ComparisonOperator: GreaterThanThreshold

# Evictions Alarm
RedisEvictionsAlarm:
  Type: AWS::CloudWatch::Alarm
  Properties:
    AlarmName: AccuNode-Redis-HighEvictions
    MetricName: Evictions
    Namespace: AWS/ElastiCache
    Threshold: 100  # per period
    ComparisonOperator: GreaterThanThreshold
```

### **Performance Insights**

```yaml
# Enable Performance Insights for RDS
PerformanceInsightsEnabled: true
PerformanceInsightsRetentionPeriod: 7  # days (free tier)
PerformanceInsightsKMSKeyId: arn:aws:kms:us-east-1:ACCOUNT:key/KMS-KEY-ID
```

### **Custom Performance Monitoring**

```python
# Database performance monitoring
import psycopg2
import time
from datetime import datetime

def monitor_db_performance():
    conn = psycopg2.connect(
        host="accunode-db-prod.cluster-xyz.us-east-1.rds.amazonaws.com",
        database="accunode_prod",
        user="monitoring_user",
        password="monitoring_password"
    )
    
    with conn.cursor() as cur:
        # Active connections
        cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
        active_connections = cur.fetchone()[0]
        
        # Long running queries
        cur.execute("""
            SELECT count(*) 
            FROM pg_stat_activity 
            WHERE state = 'active' 
            AND now() - query_start > interval '30 seconds';
        """)
        long_queries = cur.fetchone()[0]
        
        # Database size
        cur.execute("SELECT pg_size_pretty(pg_database_size('accunode_prod'));")
        db_size = cur.fetchone()[0]
        
        # Table sizes
        cur.execute("""
            SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC 
            LIMIT 5;
        """)
        table_sizes = cur.fetchall()
        
        print(f"Active connections: {active_connections}")
        print(f"Long running queries: {long_queries}")
        print(f"Database size: {db_size}")
        print("Largest tables:")
        for table in table_sizes:
            print(f"  {table[1]}: {table[2]}")
    
    conn.close()

# Redis performance monitoring
def monitor_redis_performance():
    import redis
    
    r = redis.Redis(host='accunode-redis-cluster.xyz.cache.amazonaws.com')
    
    info = r.info()
    
    # Memory metrics
    used_memory = info['used_memory_human']
    used_memory_peak = info['used_memory_peak_human']
    memory_fragmentation_ratio = info['mem_fragmentation_ratio']
    
    # Performance metrics
    total_commands_processed = info['total_commands_processed']
    instantaneous_ops_per_sec = info['instantaneous_ops_per_sec']
    keyspace_hits = info['keyspace_hits']
    keyspace_misses = info['keyspace_misses']
    hit_rate = keyspace_hits / (keyspace_hits + keyspace_misses) * 100 if keyspace_hits + keyspace_misses > 0 else 0
    
    # Connection metrics
    connected_clients = info['connected_clients']
    
    print(f"Redis Memory: {used_memory} (Peak: {used_memory_peak})")
    print(f"Fragmentation ratio: {memory_fragmentation_ratio}")
    print(f"Operations/sec: {instantaneous_ops_per_sec}")
    print(f"Hit rate: {hit_rate:.2f}%")
    print(f"Connected clients: {connected_clients}")
```

---

## 🔧 **Database Maintenance**

### **Routine Maintenance Tasks**

**Weekly Tasks:**
```sql
-- Update table statistics (runs automatically but can be manual)
ANALYZE;

-- Check for bloated tables and indexes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    pg_size_pretty(pg_indexes_size(schemaname||'.'||tablename)) as indexes_size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check for unused indexes
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE idx_tup_read = 0 AND idx_tup_fetch = 0;
```

**Monthly Tasks:**
```sql
-- Vacuum and reindex (during maintenance window)
VACUUM ANALYZE;

-- Check database bloat
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
    ROUND(100.0 * pg_relation_size(schemaname||'.'||tablename) / pg_total_relation_size(schemaname||'.'||tablename), 2) as table_ratio
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Archive old prediction data (older than 2 years)
DELETE FROM annual_predictions 
WHERE created_at < CURRENT_DATE - INTERVAL '2 years';

DELETE FROM quarterly_predictions 
WHERE created_at < CURRENT_DATE - INTERVAL '2 years';
```

### **Automated Maintenance Scripts**

```python
# Automated database maintenance
import psycopg2
from datetime import datetime, timedelta
import logging

def run_maintenance():
    logging.info("Starting database maintenance")
    
    conn = psycopg2.connect(
        host=os.getenv('DATABASE_HOST'),
        database=os.getenv('DATABASE_NAME'),
        user=os.getenv('MAINTENANCE_USER'),
        password=os.getenv('MAINTENANCE_PASSWORD')
    )
    
    with conn.cursor() as cur:
        # Update statistics
        cur.execute("ANALYZE;")
        logging.info("Statistics updated")
        
        # Clean up old sessions (older than 30 days)
        cur.execute("""
            DELETE FROM user_sessions 
            WHERE last_activity < %s
        """, (datetime.now() - timedelta(days=30),))
        
        deleted_sessions = cur.rowcount
        logging.info(f"Deleted {deleted_sessions} old sessions")
        
        # Archive old audit logs (older than 1 year)
        cur.execute("""
            DELETE FROM audit_logs 
            WHERE created_at < %s
        """, (datetime.now() - timedelta(days=365),))
        
        deleted_logs = cur.rowcount
        logging.info(f"Deleted {deleted_logs} old audit logs")
        
        conn.commit()
    
    conn.close()
    logging.info("Database maintenance completed")

# Redis maintenance
def redis_maintenance():
    import redis
    
    r = redis.Redis(host=os.getenv('REDIS_HOST'))
    
    # Get memory info before cleanup
    info_before = r.info('memory')
    used_memory_before = info_before['used_memory']
    
    # Clean up expired keys (Redis does this automatically, but we can check)
    expired_keys = r.info('stats')['expired_keys']
    
    # Check for keys that should be cleaned up manually
    # (application-specific cleanup logic)
    
    info_after = r.info('memory')
    used_memory_after = info_after['used_memory']
    
    memory_freed = used_memory_before - used_memory_after
    logging.info(f"Redis cleanup: {memory_freed} bytes freed, {expired_keys} keys expired")
```

---

## 📈 **Scaling & Optimization**

### **Vertical Scaling (Instance Sizing)**

**Scaling Thresholds:**
```yaml
# Auto-scaling based on CloudWatch metrics
ScaleUpTriggers:
  CPUUtilization: 80%      # Scale up instance size
  MemoryUtilization: 85%   # Scale up instance size
  ConnectionCount: 160     # 80% of max connections
  
ScaleDownTriggers:
  CPUUtilization: 30%      # Scale down after 30 min
  MemoryUtilization: 40%   # Scale down after 30 min
  ConnectionCount: 50      # 25% of max connections

# Instance sizing progression
InstanceSizes:
  Current: db.r6g.xlarge    # 4 vCPU, 32 GB RAM
  ScaleUp: db.r6g.2xlarge   # 8 vCPU, 64 GB RAM
  ScaleDown: db.r6g.large   # 2 vCPU, 16 GB RAM
```

### **Horizontal Scaling (Read Replicas)**

```yaml
# Read replica auto-scaling
ReadReplicaScaling:
  MinReplicas: 1
  MaxReplicas: 3
  
  ScaleOutTriggers:
    ReadIOPS: 8000          # High read load
    ReadLatency: 50         # ms average
    CPUUtilization: 70%     # on primary
    
  ScaleInTriggers:
    ReadIOPS: 2000          # Low read load
    ReadLatency: 10         # ms average
    IdleTime: 30            # minutes
```

### **Query Optimization**

```sql
-- Create performance-optimized indexes
CREATE INDEX CONCURRENTLY idx_annual_predictions_company_year 
ON annual_predictions(company_id, reporting_year);

CREATE INDEX CONCURRENTLY idx_quarterly_predictions_company_period 
ON quarterly_predictions(company_id, reporting_year, reporting_quarter);

-- Partial indexes for active records
CREATE INDEX CONCURRENTLY idx_companies_active 
ON companies(organization_id) WHERE is_active = true;

CREATE INDEX CONCURRENTLY idx_users_active_verified 
ON users(organization_id, role) WHERE is_active = true AND is_verified = true;

-- Composite indexes for common query patterns
CREATE INDEX CONCURRENTLY idx_predictions_analytics 
ON annual_predictions(created_at, risk_level, probability) 
WHERE access_level IN ('organization', 'system');

-- Text search indexes
CREATE INDEX CONCURRENTLY idx_companies_name_search 
ON companies USING gin(to_tsvector('english', name));
```

---

## 🚨 **Disaster Recovery**

### **RTO & RPO Targets**

| Scenario | RTO | RPO | Strategy |
|----------|-----|-----|----------|
| **AZ Failure** | 5 minutes | 0 | Multi-AZ failover |
| **Region Failure** | 30 minutes | 5 minutes | Cross-region replica |
| **Database Corruption** | 2 hours | 1 hour | Point-in-time recovery |
| **Complete Data Loss** | 4 hours | 24 hours | Backup restore |

### **Cross-Region Disaster Recovery**

```yaml
# Cross-region read replica for DR
DRReplica:
  DBInstanceIdentifier: accunode-db-dr-west
  SourceDBInstanceIdentifier: accunode-db-prod
  DBInstanceClass: db.r6g.xlarge
  Region: us-west-2
  BackupRetentionPeriod: 7
  
  # Automated promotion triggers
  PromotionTriggers:
    - PrimaryUnavailable: 300s  # 5 minutes
    - HealthCheckFailed: 3      # consecutive failures
    - ManualTrigger: true
```

### **Failover Procedures**

```python
# Automated failover script
import boto3
import time
import os

def execute_failover():
    rds = boto3.client('rds', region_name='us-east-1')
    rds_west = boto3.client('rds', region_name='us-west-2')
    
    # Step 1: Check primary database health
    try:
        primary_status = rds.describe_db_instances(
            DBInstanceIdentifier='accunode-db-prod'
        )['DBInstances'][0]['DBInstanceStatus']
        
        if primary_status == 'available':
            print("Primary database is healthy, failover not needed")
            return False
            
    except Exception as e:
        print(f"Primary database check failed: {e}")
    
    # Step 2: Promote read replica in DR region
    print("Promoting DR replica to primary...")
    
    try:
        rds_west.promote_read_replica(
            DBInstanceIdentifier='accunode-db-dr-west'
        )
        
        # Wait for promotion to complete
        while True:
            status = rds_west.describe_db_instances(
                DBInstanceIdentifier='accunode-db-dr-west'
            )['DBInstances'][0]['DBInstanceStatus']
            
            if status == 'available':
                print("DR replica promoted successfully")
                break
            elif status == 'modifying':
                print("Promotion in progress...")
                time.sleep(30)
            else:
                raise Exception(f"Unexpected status during promotion: {status}")
    
    except Exception as e:
        print(f"Failover failed: {e}")
        return False
    
    # Step 3: Update DNS/configuration to point to new primary
    update_application_config()
    
    # Step 4: Notify operations team
    send_failover_notification()
    
    return True

def update_application_config():
    # Update Secrets Manager with new database endpoint
    secrets = boto3.client('secretsmanager', region_name='us-west-2')
    
    # Get current secret
    secret = secrets.get_secret_value(
        SecretId='accunode/database/app-credentials'
    )
    
    # Update with new endpoint
    import json
    secret_data = json.loads(secret['SecretString'])
    secret_data['host'] = 'accunode-db-dr-west.cluster-xyz.us-west-2.rds.amazonaws.com'
    
    secrets.put_secret_value(
        SecretId='accunode/database/app-credentials',
        SecretString=json.dumps(secret_data)
    )
    
    print("Database configuration updated")
```

---

## 🔧 **Troubleshooting**

### **Common Database Issues**

**1. High CPU Utilization**
```sql
-- Identify expensive queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Check for missing indexes
SELECT 
    schemaname,
    tablename,
    seq_scan,
    seq_tup_read,
    seq_tup_read / seq_scan as avg_seq_tup_read
FROM pg_stat_user_tables
WHERE seq_scan > 0
ORDER BY seq_tup_read DESC;
```

**2. Connection Pool Exhaustion**
```sql
-- Check current connections
SELECT 
    state,
    count(*) 
FROM pg_stat_activity 
GROUP BY state;

-- Find long-running connections
SELECT 
    pid,
    usename,
    application_name,
    state,
    query_start,
    state_change,
    query
FROM pg_stat_activity 
WHERE state != 'idle' 
AND now() - query_start > interval '5 minutes'
ORDER BY query_start;
```

**3. Lock Contention**
```sql
-- Check for blocking queries
SELECT 
    blocked_locks.pid AS blocked_pid,
    blocked_activity.usename AS blocked_user,
    blocking_locks.pid AS blocking_pid,
    blocking_activity.usename AS blocking_user,
    blocked_activity.query AS blocked_statement,
    blocking_activity.query AS current_statement_in_blocking_process
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
    AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
    AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
    AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
    AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
    AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
    AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
    AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
    AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
    AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
    AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
```

### **Redis Troubleshooting**

```python
# Redis diagnostic commands
def diagnose_redis_issues():
    import redis
    
    r = redis.Redis(host=os.getenv('REDIS_HOST'))
    
    # Check Redis info
    info = r.info()
    
    # Memory issues
    if info['used_memory'] / info['maxmemory'] > 0.9:
        print("WARNING: Redis memory usage >90%")
        
        # Check memory usage by key pattern
        for pattern in ['session:*', 'cache:*', 'celery:*']:
            keys = r.keys(pattern)
            memory_usage = sum(r.memory_usage(key) for key in keys[:100])  # Sample first 100
            print(f"{pattern}: ~{memory_usage} bytes")
    
    # Check for slow operations
    slow_log = r.slowlog_get(10)
    if slow_log:
        print("Slow operations detected:")
        for entry in slow_log:
            print(f"  Duration: {entry['duration']}μs, Command: {' '.join(entry['command'])}")
    
    # Connection issues
    if info['connected_clients'] > info['maxclients'] * 0.8:
        print("WARNING: High client connection count")
    
    # Eviction issues
    if info['evicted_keys'] > 0:
        print(f"WARNING: {info['evicted_keys']} keys evicted due to memory pressure")
```

---

**Last Updated**: October 5, 2023  
**Database Version**: PostgreSQL 15.4, Redis 7.0
