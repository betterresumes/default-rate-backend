# Security Groups Configuration

Comprehensive guide for AWS Security Groups configuration for the AccuNode infrastructure.

## Overview

Security Groups act as virtual firewalls controlling inbound and outbound traffic for AWS resources. AccuNode uses multiple security groups for layered security across different components.

## Security Group Architecture

```
Internet Gateway
       │
       ▼
┌─────────────────┐
│   ALB-SG        │  Port 80/443 from 0.0.0.0/0
│ (Load Balancer) │  → ECS-SG on port 8000
└─────────────────┘
       │
       ▼
┌─────────────────┐
│   ECS-SG        │  Port 8000 from ALB-SG
│ (Fargate Tasks) │  → RDS-SG on port 5432
└─────────────────┘  → Redis-SG on port 6379
       │
       ▼
┌─────────────────┐
│   RDS-SG        │  Port 5432 from ECS-SG
│ (PostgreSQL)    │  Port 5432 from Bastion-SG
└─────────────────┘
       │
┌─────────────────┐
│  Redis-SG       │  Port 6379 from ECS-SG
│ (ElastiCache)   │
└─────────────────┘
       │
┌─────────────────┐
│  Bastion-SG     │  Port 22 from Admin IPs
│ (Jump Server)   │  → RDS-SG on port 5432
└─────────────────┘
```

## Security Groups Configuration

### 1. Application Load Balancer Security Group

**Name**: `accunode-alb-sg`
**Purpose**: Controls internet traffic to the load balancer

```hcl
resource "aws_security_group" "alb_sg" {
  name        = "accunode-alb-sg"
  description = "Security group for AccuNode Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  # HTTP (Redirect to HTTPS)
  ingress {
    description = "HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS (Main application traffic)
  ingress {
    description = "HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Outbound to ECS tasks
  egress {
    description     = "HTTP to ECS tasks"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  # Health check and other outbound
  egress {
    description = "All outbound traffic"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "AccuNode ALB Security Group"
    Environment = "production"
    Component   = "load-balancer"
  }
}
```

### 2. ECS Fargate Security Group

**Name**: `accunode-ecs-sg`
**Purpose**: Controls traffic for Fargate containers

```hcl
resource "aws_security_group" "ecs_sg" {
  name        = "accunode-ecs-sg"
  description = "Security group for AccuNode ECS Fargate tasks"
  vpc_id      = aws_vpc.main.id

  # HTTP from ALB
  ingress {
    description     = "HTTP from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  # Outbound to RDS
  egress {
    description     = "PostgreSQL to RDS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rds_sg.id]
  }

  # Outbound to Redis
  egress {
    description     = "Redis to ElastiCache"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.redis_sg.id]
  }

  # HTTPS for external API calls, package downloads
  egress {
    description = "HTTPS outbound"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP for package downloads
  egress {
    description = "HTTP outbound"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # DNS
  egress {
    description = "DNS"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "AccuNode ECS Security Group"
    Environment = "production"
    Component   = "application"
  }
}
```

### 3. RDS Security Group

**Name**: `accunode-rds-sg`
**Purpose**: Controls database access

```hcl
resource "aws_security_group" "rds_sg" {
  name        = "accunode-rds-sg"
  description = "Security group for AccuNode RDS PostgreSQL"
  vpc_id      = aws_vpc.main.id

  # PostgreSQL from ECS tasks
  ingress {
    description     = "PostgreSQL from ECS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  # PostgreSQL from Bastion (for admin access)
  ingress {
    description     = "PostgreSQL from Bastion"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  # No outbound rules (RDS doesn't initiate connections)
  
  tags = {
    Name        = "AccuNode RDS Security Group"
    Environment = "production"
    Component   = "database"
  }
}
```

### 4. Redis Security Group

**Name**: `accunode-redis-sg`
**Purpose**: Controls Redis cache access

```hcl
resource "aws_security_group" "redis_sg" {
  name        = "accunode-redis-sg"
  description = "Security group for AccuNode ElastiCache Redis"
  vpc_id      = aws_vpc.main.id

  # Redis from ECS tasks
  ingress {
    description     = "Redis from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_sg.id]
  }

  # Redis from Bastion (for debugging)
  ingress {
    description     = "Redis from Bastion"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion_sg.id]
  }

  tags = {
    Name        = "AccuNode Redis Security Group"
    Environment = "production"
    Component   = "cache"
  }
}
```

### 5. Bastion Host Security Group

**Name**: `accunode-bastion-sg`
**Purpose**: Administrative access to private resources

```hcl
resource "aws_security_group" "bastion_sg" {
  name        = "accunode-bastion-sg"
  description = "Security group for AccuNode Bastion Host"
  vpc_id      = aws_vpc.main.id

  # SSH from admin IP addresses
  ingress {
    description = "SSH from admin IPs"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = var.admin_ip_addresses  # Define in variables
  }

  # Outbound to RDS
  egress {
    description     = "PostgreSQL to RDS"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.rds_sg.id]
  }

  # Outbound to Redis
  egress {
    description     = "Redis to ElastiCache"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.redis_sg.id]
  }

  # HTTPS for package updates
  egress {
    description = "HTTPS outbound"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP for package updates
  egress {
    description = "HTTP outbound"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # DNS
  egress {
    description = "DNS"
    from_port   = 53
    to_port     = 53
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name        = "AccuNode Bastion Security Group"
    Environment = "production"
    Component   = "admin"
  }
}
```

## Variables Configuration

Define admin IP addresses in `variables.tf`:

```hcl
variable "admin_ip_addresses" {
  description = "List of IP addresses allowed SSH access to bastion host"
  type        = list(string)
  default     = [
    "203.0.113.0/32",  # Admin office IP
    "198.51.100.0/32", # Admin home IP
    "192.0.2.0/32"     # Emergency access IP
  ]
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}
```

## Security Group Rules Summary

### Traffic Flow Matrix

| Source | Destination | Port | Protocol | Purpose |
|--------|-------------|------|----------|---------|
| Internet (0.0.0.0/0) | ALB | 80 | TCP | HTTP redirect |
| Internet (0.0.0.0/0) | ALB | 443 | TCP | HTTPS traffic |
| ALB | ECS Tasks | 8000 | TCP | Application traffic |
| ECS Tasks | RDS | 5432 | TCP | Database queries |
| ECS Tasks | Redis | 6379 | TCP | Cache operations |
| ECS Tasks | Internet | 80/443 | TCP | External API calls |
| Admin IPs | Bastion | 22 | TCP | SSH access |
| Bastion | RDS | 5432 | TCP | Database admin |
| Bastion | Redis | 6379 | TCP | Cache debugging |

### Port Reference

| Service | Default Port | Security Group | Access Pattern |
|---------|--------------|----------------|----------------|
| **HTTP** | 80 | ALB-SG | Internet → ALB |
| **HTTPS** | 443 | ALB-SG | Internet → ALB |
| **FastAPI** | 8000 | ECS-SG | ALB → ECS |
| **PostgreSQL** | 5432 | RDS-SG | ECS/Bastion → RDS |
| **Redis** | 6379 | Redis-SG | ECS/Bastion → Redis |
| **SSH** | 22 | Bastion-SG | Admin IPs → Bastion |

## Deployment

### Apply Security Groups

```bash
# Deploy all security groups
terraform plan -target=module.security_groups
terraform apply -target=module.security_groups

# Deploy specific security group
terraform apply -target=aws_security_group.ecs_sg
```

### Verify Security Groups

```bash
# List all security groups
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=vpc-12345678"

# Check specific security group rules
aws ec2 describe-security-groups --group-ids sg-12345678 --query 'SecurityGroups[0].{Ingress:IpPermissions,Egress:IpPermissionsEgress}'
```

## Security Best Practices

### 1. Principle of Least Privilege
- Grant minimum required permissions
- Use security group references instead of CIDR blocks when possible
- Regularly review and audit rules

### 2. Network Segmentation
- Separate security groups by component function
- Use private subnets for databases and cache
- Limit cross-component communication

### 3. Monitoring and Logging
- Enable VPC Flow Logs
- Monitor security group changes with CloudTrail
- Set up alerts for unusual traffic patterns

### 4. Regular Security Reviews
- Audit security group rules monthly
- Remove unused security groups
- Update admin IP addresses when needed

## Troubleshooting

### Common Issues

1. **Connection Timeouts**
   ```bash
   # Check security group rules
   aws ec2 describe-security-groups --group-ids sg-12345678
   
   # Test connectivity
   telnet target-host port-number
   ```

2. **Database Connection Refused**
   ```bash
   # Verify RDS security group allows ECS traffic
   aws ec2 describe-security-groups --group-ids sg-rds-id --query 'SecurityGroups[0].IpPermissions'
   ```

3. **Health Check Failures**
   ```bash
   # Check ALB to ECS security group rules
   aws ec2 describe-security-groups --group-ids sg-alb-id sg-ecs-id
   ```

### Debugging Commands

```bash
# Show all security groups in VPC
aws ec2 describe-security-groups --filters "Name=vpc-id,Values=VPC-ID" --query 'SecurityGroups[].{GroupId:GroupId,GroupName:GroupName}'

# Check which resources use a security group
aws ec2 describe-network-interfaces --filters "Name=group-id,Values=sg-12345678" --query 'NetworkInterfaces[].{NetworkInterfaceId:NetworkInterfaceId,Description:Description}'

# Validate security group references
aws ec2 describe-security-groups --group-ids sg-12345678 --query 'SecurityGroups[0].IpPermissions[?UserIdGroupPairs[0].GroupId]'
```

---

*For additional security troubleshooting, refer to the [AWS Infrastructure Issues](../troubleshooting/aws-infrastructure-issues.md) guide.*
