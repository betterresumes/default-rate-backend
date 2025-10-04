# EC2 Database Administration Setup Guide

## Quick Setup (Automated)

Run the automated setup script:
```bash
chmod +x scripts/setup-ec2-db-admin.sh
./scripts/setup-ec2-db-admin.sh
```

## Manual Setup (Step by Step)

### 1. Create Security Group
```bash
# Create security group for EC2
aws ec2 create-security-group \
    --group-name "ec2-rds-admin-sg" \
    --description "EC2 to RDS access" \
    --region us-east-1

# Add SSH access (replace YOUR_IP with your current IP)
YOUR_IP=$(curl -s ifconfig.me)/32
aws ec2 authorize-security-group-ingress \
    --group-name "ec2-rds-admin-sg" \
    --protocol tcp \
    --port 22 \
    --cidr $YOUR_IP \
    --region us-east-1
```

### 2. Get VPC Information
```bash
# Get RDS VPC and security group info
aws rds describe-db-instances \
    --db-instance-identifier accunode-postgres \
    --region us-east-1 \
    --query 'DBInstances[0].{VPC:DBSubnetGroup.VpcId,Subnet:DBSubnetGroup.Subnets[0].SubnetIdentifier,SecurityGroup:VpcSecurityGroups[0].VpcSecurityGroupId}'
```

### 3. Allow EC2 to Access RDS
```bash
# Get the security group IDs
EC2_SG_ID=$(aws ec2 describe-security-groups --group-names "ec2-rds-admin-sg" --query 'SecurityGroups[0].GroupId' --output text)
RDS_SG_ID="sg-xxxxxxxx"  # Replace with actual RDS security group ID

# Allow EC2 security group to access RDS
aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG_ID \
    --region us-east-1
```

### 4. Launch EC2 Instance
```bash
# Get latest Amazon Linux 2 AMI
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text)

# Launch instance (replace SUBNET_ID and SECURITY_GROUP_ID)
aws ec2 run-instances \
    --image-id $AMI_ID \
    --count 1 \
    --instance-type t2.micro \
    --security-group-ids $EC2_SG_ID \
    --subnet-id subnet-xxxxxxxx \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=RDS-Admin-Instance}]" \
    --region us-east-1
```

### 5. Connect and Setup
```bash
# SSH to instance (replace PUBLIC_IP)
ssh ec2-user@PUBLIC_IP

# Install required packages
sudo yum update -y
sudo yum install -y postgresql python3 python3-pip
pip3 install psycopg2-binary
```

### 6. Create Super Admin Script on EC2
Create `/home/ec2-user/create_super_admin.py`:

```python
import psycopg2
from datetime import datetime
import hashlib
import secrets

def hash_password(password):
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def create_super_admin():
    # Database connection
    conn = psycopg2.connect(
        host="accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com",
        database="accunode",
        user="postgres",
        password=input("Enter RDS master password: "),
        port=5432
    )
    
    cur = conn.cursor()
    
    # Get admin details
    admin_email = input("Enter super admin email: ")
    admin_password = input("Enter super admin password: ")
    admin_name = input("Enter super admin full name: ")
    
    # Check if user exists
    cur.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
    if cur.fetchone():
        print("❌ User already exists!")
        return
    
    # Create user
    hashed_password = hash_password(admin_password)
    now = datetime.utcnow()
    
    cur.execute("""
        INSERT INTO users (
            email, password_hash, full_name, role, is_active, 
            is_super_admin, created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, email
    """, (admin_email, hashed_password, admin_name, 'super_admin', True, True, now, now))
    
    user_id, email = cur.fetchone()
    conn.commit()
    
    print(f"✅ Super admin created: {email} (ID: {user_id})")
    
    cur.close()
    conn.close()

if __name__ == "__main__":
    create_super_admin()
```

### 7. Run the Script
```bash
python3 create_super_admin.py
```

### 8. Cleanup (Optional)
```bash
# Terminate EC2 instance when done
aws ec2 terminate-instances --instance-ids i-xxxxxxxxx --region us-east-1

# Remove security group rules
aws ec2 revoke-security-group-ingress \
    --group-id $RDS_SG_ID \
    --protocol tcp \
    --port 5432 \
    --source-group $EC2_SG_ID
```

## Benefits of This Approach

✅ **Secure**: EC2 stays within your VPC, no public RDS exposure
✅ **Cost-effective**: t2.micro is free tier eligible
✅ **Quick**: Can be set up in 2-3 minutes
✅ **Flexible**: Full database access for any admin tasks
✅ **Temporary**: Can terminate instance immediately after use

## Security Notes

- EC2 instance is in the same VPC as RDS (secure)
- Only your current IP can SSH to EC2
- RDS only accepts connections from EC2 security group
- No public internet access to RDS required
- Can be terminated immediately after admin creation
