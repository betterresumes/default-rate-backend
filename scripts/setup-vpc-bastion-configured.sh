#!/bin/bash
# 🏗️ Setup EC2 Bastion Host in Your Private VPC for RDS Access
# This creates an EC2 instance that can access your private RDS

set -e

echo "🚀 Setting up EC2 Bastion Host for Private RDS Access"
echo "=" * 60

# You need to replace these with your actual VPC details
# Check AWS Console > VPC > Your VPC for these values
VPC_ID="vpc-0cd7231cf6acb1d4f"              # Replace with your actual VPC ID
PRIVATE_SUBNET_ID="subnet-xxxxxxx"   # Replace with a private subnet ID where RDS is accessible
PUBLIC_SUBNET_ID="subnet-xxxxxxx"    # Replace with a public subnet ID (for internet access)
AWS_REGION="us-east-1"

echo "⚠️  IMPORTANT: Update the VPC and Subnet IDs in this script first!"
echo "Current settings:"
echo "   VPC ID: $VPC_ID"
echo "   Private Subnet: $PRIVATE_SUBNET_ID"  
echo "   Public Subnet: $PUBLIC_SUBNET_ID"
echo ""

read -p "Have you updated the VPC/Subnet IDs above? (y/n): " confirmed
if [[ $confirmed != "y" ]]; then
    echo "❌ Please update the VPC and Subnet IDs first!"
    exit 1
fi

# Create IAM role for Session Manager (no SSH keys needed)
echo "📋 Creating IAM role for Session Manager access..."
aws iam create-role \
  --role-name RDS-Bastion-SSM-Role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "ec2.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }' 2>/dev/null || echo "✅ IAM role already exists"

# Attach SSM policy
aws iam attach-role-policy \
  --role-name RDS-Bastion-SSM-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name RDS-Bastion-InstanceProfile 2>/dev/null || echo "✅ Instance profile exists"

aws iam add-role-to-instance-profile \
  --instance-profile-name RDS-Bastion-InstanceProfile \
  --role-name RDS-Bastion-SSM-Role 2>/dev/null || echo "✅ Role already added"

# Wait for IAM propagation
echo "⏳ Waiting for IAM role propagation..."
sleep 10

# Create security group for bastion host
echo "🔐 Creating security group for bastion host..."
BASTION_SG_ID=$(aws ec2 create-security-group \
  --group-name rds-bastion-host-sg \
  --description "Security group for RDS bastion host" \
  --vpc-id $VPC_ID \
  --output text --query 'GroupId' 2>/dev/null || \
  aws ec2 describe-security-groups \
  --filters "Name=group-name,Values=rds-bastion-host-sg" "Name=vpc-id,Values=$VPC_ID" \
  --output text --query 'SecurityGroups[0].GroupId')

echo "✅ Bastion Security Group: $BASTION_SG_ID"

# Allow HTTPS outbound for package installation
aws ec2 authorize-security-group-egress \
  --group-id $BASTION_SG_ID \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0 2>/dev/null || echo "✅ HTTPS egress rule exists"

aws ec2 authorize-security-group-egress \
  --group-id $BASTION_SG_ID \
  --protocol tcp \
  --port 80 \
  --cidr 0.0.0.0/0 2>/dev/null || echo "✅ HTTP egress rule exists"

# Get your existing RDS security group
echo "🔍 Finding RDS security group..."
RDS_SG_ID=$(aws rds describe-db-instances \
  --db-instance-identifier accunode-postgres \
  --query 'DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId' \
  --output text 2>/dev/null)

if [[ "$RDS_SG_ID" != "None" && "$RDS_SG_ID" != "" ]]; then
    echo "✅ Found RDS Security Group: $RDS_SG_ID"
    
    # Allow PostgreSQL access from bastion to RDS
    echo "📝 Adding PostgreSQL access rule to RDS security group..."
    aws ec2 authorize-security-group-ingress \
      --group-id $RDS_SG_ID \
      --protocol tcp \
      --port 5432 \
      --source-group $BASTION_SG_ID 2>/dev/null || echo "✅ PostgreSQL rule already exists"
else
    echo "⚠️  Could not find RDS security group automatically"
    echo "   Please manually add rule to allow port 5432 from $BASTION_SG_ID"
fi

# Get latest Amazon Linux 2023 AMI
echo "🔍 Finding latest Amazon Linux 2023 AMI..."
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=al2023-ami-*" "Name=state,Values=available" \
  --query 'Images|sort_by(@, &CreationDate)[-1].[ImageId]' \
  --output text)

echo "✅ Using AMI: $AMI_ID"

# Create user data script for bastion setup
cat > bastion-userdata.sh << 'USERDATA_EOF'
#!/bin/bash
# Bastion host setup script

# Update system
dnf update -y

# Install PostgreSQL client
dnf install -y postgresql15

# Install Python and pip
dnf install -y python3 python3-pip

# Install required Python packages
pip3 install psycopg2-binary passlib[bcrypt]

# Create database connection script
cat > /home/ec2-user/connect-rds.sh << 'CONNECT_EOF'
#!/bin/bash
export PGPASSWORD="AccuNode2024!SecurePass"
psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432
CONNECT_EOF

chmod +x /home/ec2-user/connect-rds.sh
chown ec2-user:ec2-user /home/ec2-user/connect-rds.sh

# Create super admin creation script
cat > /home/ec2-user/create_super_admin.py << 'PYTHON_EOF'
#!/usr/bin/env python3
import psycopg2
import uuid
from datetime import datetime
from passlib.context import CryptContext

DB_CONFIG = {
    'host': 'accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'accunode_admin',
    'password': 'AccuNode2024!SecurePass'
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=8)

def create_super_admin():
    print("👑 CREATING SUPER ADMIN")
    
    user_id = str(uuid.uuid4())
    email = "admin@accunode.ai"
    username = "accunode"
    password = "SuperaAdmin123*"
    full_name = "accunode.ai"
    role = "super_admin"
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        print("✅ Connected to RDS!")
        
        # Check if users table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'users'
            );
        """)
        
        if not cur.fetchone()[0]:
            print("⚠️ Creating users table...")
            cur.execute("""
                CREATE TABLE users (
                    id UUID PRIMARY KEY,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    full_name VARCHAR(255),
                    role VARCHAR(50) NOT NULL DEFAULT 'user',
                    is_active BOOLEAN DEFAULT true,
                    tenant_id UUID,
                    organization_id UUID,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            print("✅ Users table created!")
        
        # Check existing user
        cur.execute("SELECT id, role FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        
        hashed_password = pwd_context.hash(password)
        
        if existing:
            cur.execute("""
                UPDATE users 
                SET role = %s, hashed_password = %s, updated_at = %s, is_active = true
                WHERE email = %s
            """, (role, hashed_password, datetime.utcnow(), email))
            print("✅ Updated existing user to super admin!")
        else:
            cur.execute("""
                INSERT INTO users (
                    id, email, username, hashed_password, full_name, 
                    role, is_active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, email, username, hashed_password, full_name,
                role, True, datetime.utcnow(), datetime.utcnow()
            ))
            print("✅ Super admin created!")
        
        conn.commit()
        
        # Verify
        cur.execute("SELECT id, email, username, role, is_active FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        print(f"\n🎉 SUPER ADMIN VERIFIED:")
        print(f"   Email: {user[1]}")
        print(f"   Username: {user[2]}")
        print(f"   Role: {user[3]}")
        print(f"   Active: {user[4]}")
        print(f"\n🔐 Credentials: {email} / {password}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_super_admin()
PYTHON_EOF

chmod +x /home/ec2-user/create_super_admin.py
chown ec2-user:ec2-user /home/ec2-user/create_super_admin.py

# Create welcome message
cat > /home/ec2-user/README.txt << 'README_EOF'
🚀 RDS BASTION HOST READY!

Available commands:
1. ./connect-rds.sh           - Connect to RDS database directly
2. python3 create_super_admin.py  - Create super admin user
3. psql commands for database management

Super Admin Details:
- Email: admin@accunode.ai
- Username: accunode  
- Password: SuperaAdmin123*

To create super admin: python3 create_super_admin.py
README_EOF

chown ec2-user:ec2-user /home/ec2-user/README.txt

echo "✅ Bastion host setup complete!"
USERDATA_EOF

# Launch the bastion instance
echo "🚀 Launching bastion host instance..."
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.micro \
  --subnet-id $PRIVATE_SUBNET_ID \
  --security-group-ids $BASTION_SG_ID \
  --iam-instance-profile Name=RDS-Bastion-InstanceProfile \
  --user-data file://bastion-userdata.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=RDS-Bastion-Host},{Key=Purpose,Value=RDS-Database-Access}]" \
  --output text --query 'Instances[0].InstanceId')

echo "✅ Bastion host launched: $INSTANCE_ID"

# Wait for instance to be running
echo "⏳ Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# Wait a bit more for user data to complete
echo "⏳ Waiting for setup to complete..."
sleep 60

echo ""
echo "🎉 BASTION HOST SETUP COMPLETE!"
echo "=" * 50
echo "Instance ID: $INSTANCE_ID"
echo "Bastion SG: $BASTION_SG_ID"
echo "RDS SG: $RDS_SG_ID"
echo ""
echo "🔗 To connect to bastion host:"
echo "   aws ssm start-session --target $INSTANCE_ID"
echo ""
echo "💾 Once connected, run:"
echo "   python3 create_super_admin.py    # Create super admin"
echo "   ./connect-rds.sh                 # Connect to database"
echo ""
echo "🗑️  To cleanup later:"
echo "   aws ec2 terminate-instances --instance-ids $INSTANCE_ID"
echo ""
echo "📋 Super Admin Credentials (after creation):"
echo "   Email: admin@accunode.ai"
echo "   Password: SuperaAdmin123*"

# Cleanup temporary files
rm -f bastion-userdata.sh
