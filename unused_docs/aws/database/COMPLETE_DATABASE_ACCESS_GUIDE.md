# 🗄️ Complete Database Access Guide

## 📋 **Overview**

This guide explains how to securely access our RDS PostgreSQL database through the EC2 bastion host. Our database is in a private subnet for security, requiring the bastion for external access.

---

## 🏗️ **Architecture**

```
Internet → Bastion EC2 (Public Subnet) → RDS PostgreSQL (Private Subnet)
```

### **Security Benefits**
- ✅ Database not directly accessible from internet
- ✅ All access logged through bastion
- ✅ Single point of access control
- ✅ VPC security groups provide additional protection

---

## 🔐 **Prerequisites**

### **Required Access**
- AWS Console access to our account (`461962182774`)
- SSH key file: `bastion-access-key.pem`
- Database credentials (ask infrastructure owner)

### **Required Tools**
- SSH client (built into macOS/Linux, PuTTY for Windows)
- PostgreSQL client (`psql`)

---

## 🚀 **Method 1: Direct SSH + Database Connection**

### **Step 1: Get Bastion Information**
```bash
# Find bastion instance details
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=AccuNode-Bastion" \
  --query 'Reservations[0].Instances[0].[InstanceId,PublicIpAddress,State.Name,Tags[?Key==`Name`].Value|[0]]' \
  --output table
```

Expected output:
```
----------------------------------------------------
|                DescribeInstances                |
|---------------+------------------+--------------|
|  i-0123456789 |  54.XXX.XXX.XXX  |  running    |
|  AccuNode-Bastion |               |             |
----------------------------------------------------
```

### **Step 2: Connect to Bastion**
```bash
# Set proper permissions for SSH key
chmod 400 bastion-access-key.pem

# SSH to bastion host
ssh -i bastion-access-key.pem ec2-user@<BASTION_PUBLIC_IP>

# Example:
# ssh -i bastion-access-key.pem ec2-user@54.XXX.XXX.XXX
```

### **Step 3: Get Database Endpoint**
```bash
# From bastion, get RDS endpoint
aws rds describe-db-instances \
  --db-instance-identifier accunode-postgres \
  --query 'DBInstances[0].Endpoint.[Address,Port]' \
  --output text

# Should show: accunode-postgres.xxxxx.us-east-1.rds.amazonaws.com 5432
```

### **Step 4: Connect to Database**
```bash
# From bastion instance
psql -h accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com \
     -U admin \
     -d accunode_production \
     -p 5432

# You'll be prompted for password
Password for user admin: [enter database password]
```

---

## 🔄 **Method 2: SSH Tunnel (Recommended for Development)**

This method lets you connect from your local machine as if the database were local.

### **Step 1: Create SSH Tunnel**
```bash
# Open terminal and create tunnel
ssh -i bastion-access-key.pem \
    -L 5432:accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com:5432 \
    ec2-user@<BASTION_PUBLIC_IP>

# This forwards local port 5432 to database through bastion
# Keep this terminal open while using the database
```

### **Step 2: Connect from Local Machine**
Open a **new terminal** and connect:
```bash
# Connect to database via tunnel
psql -h localhost -U admin -d accunode_production -p 5432

# Or use database GUI tools like pgAdmin, DBeaver, etc.
# Connection settings:
# Host: localhost
# Port: 5432
# Database: accunode_production
# Username: admin
# Password: [database password]
```

---

## 🛠️ **Database Operations**

### **Basic Database Commands**
```sql
-- List all databases
\l

-- Connect to our database
\c accunode_production

-- List all tables
\dt

-- Describe table structure
\d table_name

-- Show table sizes
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check database size
SELECT pg_size_pretty(pg_database_size('accunode_production'));

-- Exit database
\q
```

### **Application-Specific Queries**
```sql
-- Check recent predictions
SELECT 
    id, 
    tenant_id, 
    created_at, 
    prediction_type,
    status 
FROM predictions 
ORDER BY created_at DESC 
LIMIT 10;

-- Count predictions by tenant
SELECT 
    tenant_id, 
    COUNT(*) as prediction_count 
FROM predictions 
GROUP BY tenant_id 
ORDER BY prediction_count DESC;

-- Check organizations
SELECT 
    id, 
    name, 
    tenant_id, 
    created_at 
FROM organizations 
ORDER BY created_at DESC 
LIMIT 10;

-- Check active user sessions
SELECT 
    usename, 
    application_name, 
    client_addr, 
    backend_start, 
    state 
FROM pg_stat_activity 
WHERE state = 'active';

-- Check database connections
SELECT count(*) as connection_count FROM pg_stat_activity;
```

### **Performance Monitoring**
```sql
-- Check slow queries
SELECT 
    query, 
    calls, 
    total_time, 
    mean_time, 
    rows 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;

-- Check table statistics
SELECT 
    schemaname, 
    tablename, 
    n_tup_ins as inserts, 
    n_tup_upd as updates, 
    n_tup_del as deletes 
FROM pg_stat_user_tables 
ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;

-- Check index usage
SELECT 
    tablename, 
    indexname, 
    idx_scan as index_scans, 
    idx_tup_read as tuples_read 
FROM pg_stat_user_indexes 
ORDER BY idx_scan DESC;
```

---

## 📊 **Database Backup & Recovery**

### **Create Manual Backup**
```bash
# From AWS CLI (recommended)
aws rds create-db-snapshot \
  --db-instance-identifier accunode-postgres \
  --db-snapshot-identifier manual-backup-$(date +%Y%m%d-%H%M)

# List existing backups
aws rds describe-db-snapshots \
  --db-instance-identifier accunode-postgres \
  --snapshot-type manual
```

### **Export Data (from bastion)**
```bash
# Export specific table
pg_dump -h accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com \
        -U admin \
        -d accunode_production \
        -t predictions \
        --no-password \
        > predictions_backup.sql

# Export entire database
pg_dump -h accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com \
        -U admin \
        -d accunode_production \
        --no-password \
        > full_database_backup.sql

# Compress large backups
pg_dump -h accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com \
        -U admin \
        -d accunode_production \
        --no-password \
        | gzip > database_backup_$(date +%Y%m%d).sql.gz
```

---

## 🔧 **Troubleshooting**

### **Connection Issues**

#### **Cannot SSH to Bastion**
```bash
# Check bastion status
aws ec2 describe-instances \
  --filters "Name=tag:Name,Values=AccuNode-Bastion" \
  --query 'Reservations[0].Instances[0].State.Name'

# Check security group rules
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx \
  --query 'SecurityGroups[0].IpPermissions'

# Verify SSH key permissions
ls -la bastion-access-key.pem
# Should show: -r-------- (400 permissions)
```

#### **Cannot Connect to Database from Bastion**
```bash
# Test network connectivity
telnet accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com 5432

# Check RDS status
aws rds describe-db-instances \
  --db-instance-identifier accunode-postgres \
  --query 'DBInstances[0].DBInstanceStatus'

# Check database security groups
aws rds describe-db-instances \
  --db-instance-identifier accunode-postgres \
  --query 'DBInstances[0].VpcSecurityGroups'
```

#### **SSH Tunnel Not Working**
```bash
# Check if tunnel is active
netstat -an | grep 5432

# Kill existing tunnel
pkill -f "ssh.*5432"

# Recreate tunnel with verbose output
ssh -v -i bastion-access-key.pem \
    -L 5432:accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com:5432 \
    ec2-user@<BASTION_PUBLIC_IP>
```

### **Database Issues**

#### **Permission Denied**
```sql
-- Check current user permissions
SELECT current_user, session_user;

-- List user permissions
\du

-- Check table permissions
\dp table_name
```

#### **Too Many Connections**
```sql
-- Check current connections
SELECT count(*) FROM pg_stat_activity;

-- Show max connections
SHOW max_connections;

-- Kill idle connections (be careful!)
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND state_change < now() - interval '30 minutes';
```

---

## 🔒 **Security Best Practices**

### **SSH Security**
- ✅ Keep SSH key file secure (chmod 400)
- ✅ Never share SSH keys
- ✅ Use SSH agent for key management
- ✅ Close SSH sessions when done

### **Database Security**
- ✅ Never share database credentials
- ✅ Use read-only users for querying when possible
- ✅ Always close database connections
- ✅ Be careful with data export

### **Network Security**
- ✅ Only connect through bastion host
- ✅ Never attempt direct database connections
- ✅ Monitor bastion access logs
- ✅ Report any security concerns immediately

---

## 📋 **Quick Reference Commands**

### **Connect via Bastion**
```bash
# SSH to bastion
ssh -i bastion-access-key.pem ec2-user@<BASTION_IP>

# Connect to database from bastion
psql -h accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com -U admin -d accunode_production
```

### **SSH Tunnel**
```bash
# Create tunnel
ssh -i bastion-access-key.pem -L 5432:accunode-postgres.c9xq7x8qwu8v.us-east-1.rds.amazonaws.com:5432 ec2-user@<BASTION_IP>

# Connect locally
psql -h localhost -U admin -d accunode_production -p 5432
```

### **Common Queries**
```sql
-- Recent activity
SELECT * FROM predictions ORDER BY created_at DESC LIMIT 5;

-- Connection count
SELECT count(*) FROM pg_stat_activity;

-- Database size
SELECT pg_size_pretty(pg_database_size('accunode_production'));
```

---

## 🆘 **Emergency Procedures**

### **Database Unresponsive**
1. Check RDS instance status in AWS Console
2. Review CloudWatch metrics for CPU/Memory
3. Check for long-running queries
4. Consider restarting RDS instance (last resort)

### **Cannot Access Bastion**
1. Verify bastion instance is running
2. Check security group allows SSH (port 22)
3. Verify SSH key file and permissions
4. Try from different network/location

### **Data Recovery Needed**
1. Identify point-in-time for recovery
2. Create RDS snapshot before any changes
3. Use point-in-time recovery if available
4. Contact AWS support if needed

---

## 📞 **Getting Help**

### **Infrastructure Issues**
- Check AWS Console RDS dashboard
- Review CloudWatch logs and metrics
- Contact infrastructure owner: Pranit

### **Database Performance**
- Run performance queries above
- Check CloudWatch RDS metrics
- Consider query optimization

### **Access Issues**  
- Verify AWS IAM permissions
- Check network connectivity
- Validate SSH key and database credentials

---

*Database Access Guide v1.0 | Updated: Oct 4, 2025 | Owner: AccuNode Team*
