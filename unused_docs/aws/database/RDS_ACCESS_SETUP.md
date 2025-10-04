# 🔐 Private RDS Database Access Setup

## Overview
Your RDS database is private (which is good for security), but you need access for administration and super admin setup. Here are the recommended approaches:

## Option 1: 🚀 **AWS Systems Manager Session Manager (Recommended)**

### Create EC2 Bastion Host with Session Manager

1. **Create EC2 Instance**:
```bash
# Create security group for bastion
aws ec2 create-security-group \
  --group-name rds-bastion-sg \
  --description "Bastion host for RDS access" \
  --vpc-id vpc-xxxxxxxxx

# Add inbound rule for PostgreSQL (only from bastion)
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxxxxxx \
  --protocol tcp \
  --port 5432 \
  --source-group sg-bastion-xxxxxxxxx
```

2. **Launch Bastion Instance**:
```bash
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.micro \
  --key-name your-key-name \
  --security-group-ids sg-xxxxxxxxx \
  --subnet-id subnet-xxxxxxxxx \
  --iam-instance-profile Name=SSM-Role \
  --user-data file://bastion-user-data.sh \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=RDS-Bastion}]'
```

### Bastion User Data Script

Create `bastion-user-data.sh`:
```bash
#!/bin/bash
yum update -y
yum install -y postgresql15

# Install Python and required packages
yum install -y python3 python3-pip git
pip3 install psycopg2-binary sqlalchemy fastapi uvicorn python-dotenv passlib[bcrypt]

# Install AWS CLI v2
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Setup PostgreSQL client
echo 'export PATH=/usr/pgsql-15/bin:$PATH' >> /home/ec2-user/.bashrc
```

### Connect via Session Manager
```bash
# Connect to bastion host
aws ssm start-session --target i-xxxxxxxxxxxxxxxxx

# Inside bastion, connect to RDS
psql -h your-rds-endpoint.rds.amazonaws.com -U your-username -d your-database
```

## Option 2: 🔧 **AWS RDS Proxy (Production Grade)**

### Create RDS Proxy
```bash
aws rds create-db-proxy \
  --db-proxy-name default-rate-proxy \
  --engine-family POSTGRESQL \
  --auth '{
    "AuthScheme": "SECRETS",
    "SecretArn": "arn:aws:secretsmanager:us-east-1:461962182774:secret:rds-db-credentials/cluster-xxxxx",
    "IAMAuth": "DISABLED"
  }' \
  --role-arn arn:aws:iam::461962182774:role/RDSProxyRole \
  --vpc-subnet-ids subnet-xxxxxxxxx subnet-yyyyyyyyy \
  --vpc-security-group-ids sg-xxxxxxxxx
```

## Option 3: 🌐 **VPN Connection (For Development)**

### Create Client VPN Endpoint
```bash
aws ec2 create-client-vpn-endpoint \
  --client-cidr-block 172.31.0.0/22 \
  --server-certificate-arn arn:aws:acm:us-east-1:461962182774:certificate/xxxxx \
  --authentication-options Type=certificate-authentication,MutualAuthentication={ClientRootCertificateChainArn=arn:aws:acm:us-east-1:461962182774:certificate/xxxxx} \
  --connection-log-options Enabled=false
```

## Recommended Approach: **Session Manager + Bastion Host**

This is the most secure and AWS-native approach. Let's implement it:
