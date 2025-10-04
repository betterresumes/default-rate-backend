#!/bin/bash

# EC2 Setup Script for RDS Database Administration
# This script sets up an EC2 instance in the same VPC as your RDS for secure database access

echo "🚀 Setting up EC2 instance for RDS database administration..."
echo "=================================================="

# Configuration - Update these values
RDS_ENDPOINT="accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com"
DB_NAME="accunode"
DB_USER="postgres"
REGION="us-east-1"

# Step 1: Create security group for EC2 instance
echo "📋 Step 1: Creating security group for EC2 instance..."

SECURITY_GROUP_ID=$(aws ec2 create-security-group \
    --group-name "ec2-rds-admin-sg" \
    --description "Security group for EC2 instance to access RDS" \
    --region $REGION \
    --output text --query 'GroupId' 2>/dev/null)

if [ $? -eq 0 ]; then
    echo "✅ Security group created: $SECURITY_GROUP_ID"
else
    echo "⚠️ Security group might already exist, getting existing one..."
    SECURITY_GROUP_ID=$(aws ec2 describe-security-groups \
        --group-names "ec2-rds-admin-sg" \
        --region $REGION \
        --output text --query 'SecurityGroups[0].GroupId' 2>/dev/null)
fi

echo "🔧 Security Group ID: $SECURITY_GROUP_ID"

# Step 2: Add SSH access rule (only from your current IP)
echo "📋 Step 2: Adding SSH access rule..."

# Get your current public IP
YOUR_IP=$(curl -s ifconfig.me)/32
echo "🌐 Your current IP: $YOUR_IP"

aws ec2 authorize-security-group-ingress \
    --group-id $SECURITY_GROUP_ID \
    --protocol tcp \
    --port 22 \
    --cidr $YOUR_IP \
    --region $REGION 2>/dev/null

echo "✅ SSH access added for your IP"

# Step 3: Get VPC and subnet information from existing RDS
echo "📋 Step 3: Getting VPC information from RDS..."

RDS_INFO=$(aws rds describe-db-instances \
    --db-instance-identifier accunode-postgres \
    --region $REGION \
    --output json 2>/dev/null)

if [ $? -eq 0 ]; then
    VPC_ID=$(echo $RDS_INFO | jq -r '.DBInstances[0].DBSubnetGroup.VpcId')
    SUBNET_ID=$(echo $RDS_INFO | jq -r '.DBInstances[0].DBSubnetGroup.Subnets[0].SubnetIdentifier')
    RDS_SECURITY_GROUP=$(echo $RDS_INFO | jq -r '.DBInstances[0].VpcSecurityGroups[0].VpcSecurityGroupId')
    
    echo "✅ VPC ID: $VPC_ID"
    echo "✅ Subnet ID: $SUBNET_ID"
    echo "✅ RDS Security Group: $RDS_SECURITY_GROUP"
else
    echo "❌ Could not retrieve RDS information. Please check RDS instance name and permissions."
    exit 1
fi

# Step 4: Allow EC2 security group to access RDS
echo "📋 Step 4: Allowing EC2 to access RDS..."

aws ec2 authorize-security-group-ingress \
    --group-id $RDS_SECURITY_GROUP \
    --protocol tcp \
    --port 5432 \
    --source-group $SECURITY_GROUP_ID \
    --region $REGION 2>/dev/null

echo "✅ EC2 access to RDS configured"

# Step 5: Create EC2 instance
echo "📋 Step 5: Creating EC2 instance..."

# Get the latest Amazon Linux 2 AMI
AMI_ID=$(aws ec2 describe-images \
    --owners amazon \
    --filters "Name=name,Values=amzn2-ami-hvm-*-x86_64-gp2" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --region $REGION \
    --output text)

echo "🖥️ Using AMI: $AMI_ID"

# Create user data script for EC2
cat > /tmp/ec2-userdata.sh << 'EOF'
#!/bin/bash
yum update -y
yum install -y postgresql python3 python3-pip

# Install Python packages
pip3 install psycopg2-binary python-dotenv

# Create directory for scripts
mkdir -p /home/ec2-user/scripts
chown ec2-user:ec2-user /home/ec2-user/scripts

# Create the super admin script
cat > /home/ec2-user/scripts/create_super_admin.py << 'PYTHON_EOF'
import psycopg2
import os
import sys
from datetime import datetime
import hashlib
import secrets

def hash_password(password):
    """Hash password using SHA-256 with salt"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def create_super_admin():
    # Database configuration
    DB_HOST = "accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com"
    DB_NAME = "accunode"
    DB_USER = "postgres"
    
    # Get password from environment or prompt
    db_password = os.getenv("DB_PASSWORD")
    if not db_password:
        db_password = input("Enter RDS master password: ")
    
    admin_email = input("Enter super admin email: ")
    admin_password = input("Enter super admin password: ")
    admin_name = input("Enter super admin full name: ")
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=db_password,
            port=5432
        )
        
        cur = conn.cursor()
        
        # Check if user already exists
        cur.execute("SELECT id FROM users WHERE email = %s", (admin_email,))
        existing_user = cur.fetchone()
        
        if existing_user:
            print(f"❌ User with email {admin_email} already exists!")
            return
        
        # Hash the password
        hashed_password = hash_password(admin_password)
        
        # Insert super admin user
        insert_query = """
        INSERT INTO users (
            email, password_hash, full_name, role, is_active, 
            is_super_admin, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s
        ) RETURNING id, email
        """
        
        now = datetime.utcnow()
        cur.execute(insert_query, (
            admin_email,
            hashed_password,
            admin_name,
            'super_admin',
            True,
            True,
            now,
            now
        ))
        
        user_id, email = cur.fetchone()
        conn.commit()
        
        print(f"✅ Super admin created successfully!")
        print(f"   User ID: {user_id}")
        print(f"   Email: {email}")
        print(f"   Name: {admin_name}")
        print(f"   Role: super_admin")
        
        # Verify the user was created
        cur.execute("SELECT id, email, full_name, role, is_super_admin FROM users WHERE id = %s", (user_id,))
        user_data = cur.fetchone()
        
        if user_data:
            print("\n🔍 Verification:")
            print(f"   ID: {user_data[0]}")
            print(f"   Email: {user_data[1]}")
            print(f"   Name: {user_data[2]}")
            print(f"   Role: {user_data[3]}")
            print(f"   Is Super Admin: {user_data[4]}")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    create_super_admin()
PYTHON_EOF

# Create database exploration script
cat > /home/ec2-user/scripts/explore_database.py << 'PYTHON_EOF'
import psycopg2
import os

def explore_database():
    # Database configuration
    DB_HOST = "accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com"
    DB_NAME = "accunode"
    DB_USER = "postgres"
    
    # Get password from environment or prompt
    db_password = os.getenv("DB_PASSWORD")
    if not db_password:
        db_password = input("Enter RDS master password: ")
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=db_password,
            port=5432
        )
        
        cur = conn.cursor()
        
        # List all tables
        print("\n📋 Available Tables:")
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cur.fetchall()
        for i, (table_name,) in enumerate(tables, 1):
            print(f"   {i}. {table_name}")
        
        # Show users table structure and data
        print("\n👥 Users Table:")
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'users' ORDER BY ordinal_position")
        columns = cur.fetchall()
        
        print("   Columns:")
        for col_name, data_type in columns:
            print(f"     - {col_name}: {data_type}")
        
        # Show sample users (without passwords)
        cur.execute("SELECT id, email, full_name, role, is_active, is_super_admin, created_at FROM users LIMIT 5")
        users = cur.fetchall()
        
        if users:
            print("\n   Sample Users:")
            for user in users:
                print(f"     ID: {user[0]}, Email: {user[1]}, Role: {user[3]}, Super Admin: {user[5]}")
        else:
            print("   No users found in database")
        
        print(f"\n📊 Total Users: {len(users) if users else 0}")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    explore_database()
PYTHON_EOF

# Make scripts executable
chmod +x /home/ec2-user/scripts/*.py
chown ec2-user:ec2-user /home/ec2-user/scripts/*.py

# Create instructions file
cat > /home/ec2-user/instructions.txt << 'INSTRUCTIONS_EOF'
🎯 EC2 Database Administration Setup Complete!

📂 Available Scripts:
   /home/ec2-user/scripts/create_super_admin.py - Create super admin user
   /home/ec2-user/scripts/explore_database.py - Explore database structure

🚀 How to use:

1. Create Super Admin:
   cd /home/ec2-user/scripts
   python3 create_super_admin.py

2. Explore Database:
   python3 explore_database.py

3. Direct PostgreSQL Access:
   psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U postgres -d accunode

🔐 Security Notes:
- This EC2 instance is in the same VPC as your RDS
- Only your IP can SSH to this instance
- RDS accepts connections only from this EC2 security group
- Remember to terminate this instance when done

📋 Next Steps:
1. SSH to this instance
2. Run the create_super_admin.py script
3. Verify the admin user was created
4. Terminate this instance (optional)
INSTRUCTIONS_EOF

chown ec2-user:ec2-user /home/ec2-user/instructions.txt

echo "✅ EC2 instance setup complete!"
EOF

# Launch EC2 instance
INSTANCE_ID=$(aws ec2 run-instances \
    --image-id $AMI_ID \
    --count 1 \
    --instance-type t2.micro \
    --security-group-ids $SECURITY_GROUP_ID \
    --subnet-id $SUBNET_ID \
    --user-data file:///tmp/ec2-userdata.sh \
    --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=RDS-Admin-Instance}]" \
    --region $REGION \
    --output text --query 'Instances[0].InstanceId')

if [ $? -eq 0 ]; then
    echo "✅ EC2 instance created: $INSTANCE_ID"
else
    echo "❌ Failed to create EC2 instance"
    exit 1
fi

# Wait for instance to be running
echo "⏳ Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID --region $REGION

# Get instance public IP
PUBLIC_IP=$(aws ec2 describe-instances \
    --instance-ids $INSTANCE_ID \
    --region $REGION \
    --output text --query 'Reservations[0].Instances[0].PublicIpAddress')

echo ""
echo "🎉 EC2 Setup Complete!"
echo "======================"
echo "Instance ID: $INSTANCE_ID"
echo "Public IP: $PUBLIC_IP"
echo "Security Group: $SECURITY_GROUP_ID"
echo ""
echo "🔐 SSH Connection:"
echo "ssh ec2-user@$PUBLIC_IP"
echo ""
echo "📋 Once connected, run:"
echo "cat instructions.txt"
echo "cd scripts && python3 create_super_admin.py"
echo ""
echo "🗑️ Cleanup (when done):"
echo "aws ec2 terminate-instances --instance-ids $INSTANCE_ID --region $REGION"
echo ""

# Clean up temporary file
rm -f /tmp/ec2-userdata.sh

echo "✅ Setup script completed successfully!"
