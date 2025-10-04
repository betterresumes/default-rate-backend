#!/bin/bash
# 🚀 Fastest Lambda Creation for Super Admin (One Command)
# This creates a Lambda that can run SQL to create super admin

echo "🚀 Ultra-Simple Lambda Super Admin Creator"
echo "💰 Cost: $0.0000002 per execution (practically FREE!)"

# Create a simple Lambda function that just returns the SQL commands needed
aws lambda create-function \
  --function-name quick-super-admin \
  --runtime python3.9 \
  --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/lambda-execution-role \
  --handler index.handler \
  --zip-file fileb://<(cat << 'EOF' | zip -
import json
import uuid
from datetime import datetime

def handler(event, context):
    """
    Returns SQL commands to create super admin user
    """
    user_id = str(uuid.uuid4())
    
    # SQL commands to run
    sql_commands = [
        # Create table if not exists
        """
        CREATE TABLE IF NOT EXISTS users (
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
        """,
        
        # Insert super admin (with simple hash)
        f"""
        INSERT INTO users (
            id, email, username, hashed_password, full_name, 
            role, is_active, created_at, updated_at
        ) VALUES (
            '{user_id}',
            'admin@accunode.ai',
            'accunode',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBVDoVk4HMJb8.', -- bcrypt of 'SuperaAdmin123*'
            'accunode.ai',
            'super_admin',
            true,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (email) DO UPDATE SET
            role = 'super_admin',
            hashed_password = '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBVDoVk4HMJb8.',
            updated_at = CURRENT_TIMESTAMP;
        """,
        
        # Verify creation
        "SELECT id, email, username, role, is_active FROM users WHERE role = 'super_admin';"
    ]
    
    return {
        'statusCode': 200,
        'body': {
            'message': 'Super admin SQL commands generated',
            'sql_commands': sql_commands,
            'credentials': {
                'email': 'admin@accunode.ai',
                'username': 'accunode', 
                'password': 'SuperaAdmin123*',
                'role': 'super_admin'
            },
            'instructions': [
                '1. Connect to RDS via any method (CloudShell, pgAdmin, etc.)',
                '2. Run the SQL commands above',
                '3. Super admin will be created/updated',
                '4. Use credentials to access admin APIs'
            ]
        }
    }
EOF
) \
  --timeout 30 \
  --memory-size 128 \
  --description "Generate SQL for super admin creation" || echo "Function exists"

echo "🧪 Running Lambda to get SQL commands..."
aws lambda invoke \
  --function-name quick-super-admin \
  --payload '{}' \
  response.json

echo ""
echo "📋 SQL Commands to Create Super Admin:"
echo "=" * 50

# Extract and format the SQL commands
python3 -c "
import json
with open('response.json', 'r') as f:
    data = json.load(f)
body = json.loads(data['body'])
for i, cmd in enumerate(body['sql_commands'], 1):
    print(f'-- Command {i}:')
    print(cmd.strip())
    print()
"

echo ""
echo "🔐 Super Admin Credentials:"
echo "   Email: admin@accunode.ai"
echo "   Username: accunode"
echo "   Password: SuperaAdmin123*"
echo ""
echo "💡 Next Steps:"
echo "1. Use ANY method to connect to your RDS"
echo "2. Run the SQL commands above"
echo "3. Super admin will be ready!"

rm -f response.json
