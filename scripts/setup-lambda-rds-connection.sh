#!/bin/bash
# 🚀 Use AWS RDS "Set up Lambda connection" Feature
# This uses AWS's built-in Lambda-RDS integration (EASIEST!)

echo "🚀 AWS RDS Lambda Connection Setup"
echo "This uses AWS Console's built-in 'Set up Lambda connection' feature"
echo "=" * 60

# Step 1: Create the Lambda function first (without VPC)
FUNCTION_NAME="rds-superadmin-creator"
echo "📦 Creating Lambda function..."

# Create simple Lambda function code
cat > lambda_function.py << 'EOF'
import json
import psycopg2
import uuid
from datetime import datetime

def simple_hash(password):
    """Simple hash - replace with proper bcrypt in production"""
    import hashlib
    return hashlib.sha256(password.encode()).hexdigest()

def lambda_handler(event, context):
    print("🚀 Creating Super Admin in RDS")
    
    # RDS connection details
    db_config = {
        'host': 'accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com',
        'port': 5432,
        'database': 'postgres',
        'user': 'accunode_admin',
        'password': 'AccuNode2024!SecurePass'
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cur = conn.cursor()
        
        # Create users table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
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
        
        # Super admin details
        email = "admin@accunode.ai"
        username = "accunode"
        password = "SuperaAdmin123*"
        hashed_password = simple_hash(password)
        
        # Insert or update super admin
        cur.execute("""
            INSERT INTO users (email, username, hashed_password, full_name, role, is_active)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (email) 
            DO UPDATE SET 
                role = 'super_admin',
                hashed_password = EXCLUDED.hashed_password,
                is_active = true,
                updated_at = CURRENT_TIMESTAMP;
        """, (email, username, hashed_password, "accunode.ai", "super_admin", True))
        
        conn.commit()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Super admin created successfully!',
                'credentials': {
                    'email': email,
                    'username': username,
                    'password': password
                }
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()
EOF

# Create deployment package
zip lambda-deployment.zip lambda_function.py

# Create IAM role for Lambda
aws iam create-role \
  --role-name lambda-rds-role \
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
  }' 2>/dev/null || echo "✅ Role exists"

# Attach basic execution policy
aws iam attach-role-policy \
  --role-name lambda-rds-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Wait for IAM
sleep 10

# Get account ID and create role ARN
ACCOUNT_ID=$(aws sts get-caller-identity --output text --query Account)
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/lambda-rds-role"

# Create Lambda function (without VPC initially)
aws lambda create-function \
  --function-name $FUNCTION_NAME \
  --runtime python3.9 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 30 \
  --description "Create super admin in RDS" \
  2>/dev/null || \
aws lambda update-function-code \
  --function-name $FUNCTION_NAME \
  --zip-file fileb://lambda-deployment.zip

echo "✅ Lambda function created: $FUNCTION_NAME"
echo ""
echo "🎯 NEXT STEPS (Manual in AWS Console):"
echo "=" * 50
echo ""
echo "1. Go to RDS Console → Databases → accunode-postgres"
echo "2. Scroll down to 'Connected compute resources'"
echo "3. Click 'Set up Lambda connection' button"
echo "4. Select your Lambda function: $FUNCTION_NAME"
echo "5. AWS will automatically:"
echo "   - Configure VPC settings"
echo "   - Set up security groups"
echo "   - Add Lambda to RDS subnet"
echo ""
echo "6. After setup completes, test the Lambda:"
echo "   aws lambda invoke --function-name $FUNCTION_NAME --payload '{}' result.json"
echo ""
echo "🔐 Expected Super Admin Credentials:"
echo "   Email: admin@accunode.ai"
echo "   Username: accunode"
echo "   Password: SuperaAdmin123*"
echo ""
echo "💰 Cost: ~$0.0000002 per execution (practically FREE!)"

# Cleanup
rm -f lambda_function.py lambda-deployment.zip
