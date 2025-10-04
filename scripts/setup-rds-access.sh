#!/bin/bash
# 🚀 Setup script for RDS access via bastion host

set -e

# Configuration
AWS_REGION="us-east-1"
ACCOUNT_ID="461962182774"
VPC_ID="vpc-xxxxxxxxx"  # Replace with your VPC ID
SUBNET_ID="subnet-xxxxxxxxx"  # Replace with your private subnet ID
KEY_NAME="your-key-name"  # Replace with your EC2 key pair name

echo "🏗️  Setting up RDS access infrastructure..."

# Create IAM role for SSM access
echo "📋 Creating IAM role for Session Manager..."
aws iam create-role \
  --role-name EC2-SSM-Role \
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
  }' || echo "Role already exists"

# Attach SSM managed policy
aws iam attach-role-policy \
  --role-name EC2-SSM-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Create instance profile
aws iam create-instance-profile \
  --instance-profile-name EC2-SSM-InstanceProfile || echo "Profile already exists"

aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-SSM-InstanceProfile \
  --role-name EC2-SSM-Role || echo "Role already added"

# Create security group for bastion host
echo "🔐 Creating security group for bastion host..."
BASTION_SG_ID=$(aws ec2 create-security-group \
  --group-name rds-bastion-sg \
  --description "Bastion host for RDS database access" \
  --vpc-id $VPC_ID \
  --output text --query 'GroupId' 2>/dev/null || \
  aws ec2 describe-security-groups \
  --group-names rds-bastion-sg \
  --output text --query 'SecurityGroups[0].GroupId')

echo "✅ Bastion Security Group ID: $BASTION_SG_ID"

# Create security group for RDS access
echo "🔐 Creating security group for RDS access..."
RDS_SG_ID=$(aws ec2 create-security-group \
  --group-name rds-admin-access-sg \
  --description "Allow access to RDS from bastion host" \
  --vpc-id $VPC_ID \
  --output text --query 'GroupId' 2>/dev/null || \
  aws ec2 describe-security-groups \
  --group-names rds-admin-access-sg \
  --output text --query 'SecurityGroups[0].GroupId')

echo "✅ RDS Security Group ID: $RDS_SG_ID"

# Add rule to allow PostgreSQL access from bastion to RDS
echo "📝 Adding PostgreSQL access rule..."
aws ec2 authorize-security-group-ingress \
  --group-id $RDS_SG_ID \
  --protocol tcp \
  --port 5432 \
  --source-group $BASTION_SG_ID 2>/dev/null || echo "Rule already exists"

# Get latest Amazon Linux 2 AMI
echo "🔍 Finding latest Amazon Linux 2 AMI..."
AMI_ID=$(aws ec2 describe-images \
  --owners amazon \
  --filters "Name=name,Values=amzn2-ami-hvm-*" \
  --query 'Images|sort_by(@, &CreationDate)[-1].[ImageId]' \
  --output text)

echo "✅ Using AMI: $AMI_ID"

# Create user data script
cat > bastion-user-data.sh << 'EOF'
#!/bin/bash
yum update -y

# Install PostgreSQL client
amazon-linux-extras install postgresql14 -y

# Install Python 3 and pip
yum install -y python3 python3-pip git

# Install required Python packages
pip3 install --user psycopg2-binary sqlalchemy fastapi uvicorn python-dotenv passlib[bcrypt] pandas

# Install AWS CLI v2
cd /tmp
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
./aws/install

# Setup environment for ec2-user
echo 'export PATH=/usr/bin:$PATH' >> /home/ec2-user/.bashrc
echo 'export PATH=/home/ec2-user/.local/bin:$PATH' >> /home/ec2-user/.bashrc

# Create database connection script
cat > /home/ec2-user/connect-db.sh << 'DBEOF'
#!/bin/bash
# Database connection script
export PGPASSWORD="npg_FRS5ptsg3QcE"
psql -h ep-snowy-darkness-adw0r2ai-pooler.c-2.us-east-1.aws.neon.tech -U neondb_owner -d neondb
DBEOF

chmod +x /home/ec2-user/connect-db.sh
chown ec2-user:ec2-user /home/ec2-user/connect-db.sh

# Create admin scripts directory
mkdir -p /home/ec2-user/admin-scripts
chown ec2-user:ec2-user /home/ec2-user/admin-scripts

echo "✅ Bastion host setup complete!"
EOF

# Launch bastion instance
echo "🚀 Launching bastion host instance..."
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI_ID \
  --instance-type t3.micro \
  --security-group-ids $BASTION_SG_ID \
  --subnet-id $SUBNET_ID \
  --iam-instance-profile Name=EC2-SSM-InstanceProfile \
  --user-data file://bastion-user-data.sh \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=RDS-Admin-Bastion},{Key=Purpose,Value=Database-Administration}]" \
  --output text --query 'Instances[0].InstanceId')

echo "✅ Bastion host launched: $INSTANCE_ID"

# Wait for instance to be running
echo "⏳ Waiting for instance to be running..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

echo "🎉 Setup complete!"
echo ""
echo "📋 Connection Information:"
echo "   Instance ID: $INSTANCE_ID"
echo "   Bastion SG:  $BASTION_SG_ID"
echo "   RDS SG:      $RDS_SG_ID"
echo ""
echo "🔗 To connect:"
echo "   aws ssm start-session --target $INSTANCE_ID"
echo ""
echo "💾 Inside the bastion host:"
echo "   ./connect-db.sh  # Connect to database"
echo ""
echo "🗑️  To cleanup later:"
echo "   aws ec2 terminate-instances --instance-ids $INSTANCE_ID"

# Clean up temporary files
rm -f bastion-user-data.sh
