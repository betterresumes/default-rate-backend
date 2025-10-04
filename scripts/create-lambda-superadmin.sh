#!/bin/bash
# 🚀 Create Lambda Function to Access Private RDS and Create Super Admin
# This is MUCH cheaper than EC2 - only pay when you run it!

set -e

echo "🚀 Creating Lambda Function for RDS Super Admin Creation"
echo "Cost: ~$0.0000002 per execution (practically FREE!)"
echo "=" * 60

# Configuration
FUNCTION_NAME="rds-super-admin-creator"
ROLE_NAME="lambda-rds-access-role"
AWS_REGION="us-east-1"

echo "📋 Function Configuration:"
echo "   Function Name: $FUNCTION_NAME"
echo "   Role Name: $ROLE_NAME"
echo "   Region: $AWS_REGION"

# Create IAM role for Lambda
echo ""
echo "📋 Creating IAM role for Lambda..."
aws iam create-role \
  --role-name $ROLE_NAME \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }' 2>/dev/null || echo "✅ Role already exists"

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name $ROLE_NAME \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create VPC execution policy (if Lambda needs VPC access)
cat > lambda-vpc-policy.json << 'EOF'
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "ec2:CreateNetworkInterface",
                "ec2:DescribeNetworkInterfaces",
                "ec2:DeleteNetworkInterface",
                "ec2:AttachNetworkInterface",
                "ec2:DetachNetworkInterface"
            ],
            "Resource": "*"
        }
    ]
}
EOF

aws iam put-role-policy \
  --role-name $ROLE_NAME \
  --policy-name LambdaVPCExecutionPolicy \
  --policy-document file://lambda-vpc-policy.json

echo "✅ IAM role configured"

# Wait for IAM propagation
echo "⏳ Waiting for IAM role propagation..."
sleep 15

# Create Lambda function code
echo ""
echo "📝 Creating Lambda function code..."
mkdir -p lambda-package
cd lambda-package

# Create the Lambda function
cat > lambda_function.py << 'LAMBDA_EOF'
import json
import psycopg2
import uuid
from datetime import datetime
import hashlib
import hmac
import base64

def hash_password(password):
    """Simple bcrypt-like hash for demo - use proper bcrypt in production"""
    import hashlib
    salt = "supersalt123"
    return hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()

def lambda_handler(event, context):
    print("🚀 Lambda Super Admin Creator Started")
    
    # RDS Configuration
    db_config = {
        'host': 'accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com',
        'port': 5432,
        'database': 'postgres',
        'user': 'accunode_admin',
        'password': 'AccuNode2024!SecurePass'
    }
    
    # Super admin details
    user_id = str(uuid.uuid4())
    email = "admin@accunode.ai"
    username = "accunode"
    password = "SuperaAdmin123*"
    full_name = "accunode.ai"
    role = "super_admin"
    
    result = {
        'statusCode': 200,
        'body': {
            'message': '',
            'user_created': False,
            'credentials': {
                'email': email,
                'username': username,
                'password': password
            }
        }
    }
    
    try:
        print("🔗 Connecting to RDS...")
        conn = psycopg2.connect(**db_config)
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
            result['body']['table_created'] = True
            print("✅ Users table created!")
        
        # Check existing user
        cur.execute("SELECT id, role FROM users WHERE email = %s", (email,))
        existing = cur.fetchone()
        
        hashed_password = hash_password(password)
        
        if existing:
            # Update existing user
            cur.execute("""
                UPDATE users 
                SET role = %s, hashed_password = %s, updated_at = %s, is_active = true
                WHERE email = %s
            """, (role, hashed_password, datetime.utcnow(), email))
            result['body']['message'] = "Updated existing user to super admin!"
            result['body']['user_updated'] = True
            print("✅ Updated existing user to super admin!")
        else:
            # Create new user
            cur.execute("""
                INSERT INTO users (
                    id, email, username, hashed_password, full_name, 
                    role, is_active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, email, username, hashed_password, full_name,
                role, True, datetime.utcnow(), datetime.utcnow()
            ))
            result['body']['message'] = "Super admin created successfully!"
            result['body']['user_created'] = True
            print("✅ Super admin created!")
        
        conn.commit()
        
        # Verify
        cur.execute("SELECT id, email, username, role, is_active FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        if user:
            result['body']['verification'] = {
                'id': str(user[0]),
                'email': user[1],
                'username': user[2], 
                'role': user[3],
                'active': user[4]
            }
            print(f"🎉 SUPER ADMIN VERIFIED: {user[1]} ({user[3]})")
        
        cur.close()
        conn.close()
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        result['statusCode'] = 500
        result['body']['error'] = str(e)
        return result
LAMBDA_EOF

# Create requirements for psycopg2 layer
cat > requirements.txt << 'REQ_EOF'
psycopg2-binary==2.9.7
REQ_EOF

# Install dependencies
pip3 install -r requirements.txt -t .

# Create deployment package
zip -r ../lambda-function.zip .
cd ..

echo "✅ Lambda package created: lambda-function.zip"

# Get account ID for role ARN
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE_NAME"

echo "📦 Deploying Lambda function..."

# Create Lambda function
aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --runtime python3.9 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda-function.zip \
  --timeout 30 \
  --memory-size 128 \
  --description "Create super admin user in private RDS database" \
  2>/dev/null || \
  
# Update if already exists
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://lambda-function.zip

echo "✅ Lambda function deployed!"

# Test the function
echo ""
echo "🧪 Testing Lambda function..."
RESULT=$(aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --payload '{}' \
  --output json \
  response.json)

echo "📋 Lambda execution result:"
cat response.json | jq '.'

echo ""
echo "🎉 LAMBDA SETUP COMPLETE!"
echo "=" * 50
echo "💰 Cost per execution: ~$0.0000002 (practically FREE!)"
echo "📊 Function: $FUNCTION_NAME"
echo "🔗 To run again: aws lambda invoke --function-name $FUNCTION_NAME --payload '{}' response.json"
echo ""
echo "🔐 Super Admin Credentials:"
echo "   Email: admin@accunode.ai"
echo "   Password: SuperaAdmin123*"
echo "   Username: accunode"
echo ""
echo "🗑️  To cleanup:"
echo "   aws lambda delete-function --function-name $FUNCTION_NAME"
echo "   aws iam delete-role --role-name $ROLE_NAME"

# Cleanup
rm -rf lambda-package lambda-function.zip lambda-vpc-policy.json response.json
