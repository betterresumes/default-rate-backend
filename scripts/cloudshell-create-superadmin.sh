#!/bin/bash
# 🌩️ AWS CloudShell Script to Create Super Admin in RDS
# Copy and paste this entire script into AWS CloudShell

echo "🚀 Creating Super Admin in Private RDS via CloudShell"
echo "=" * 60

# Install PostgreSQL client if not available
echo "📦 Installing PostgreSQL client..."
sudo yum install -y postgresql15 python3-pip

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip3 install --user psycopg2-binary passlib[bcrypt]

# Create Python script for super admin creation
cat > create_super_admin.py << 'EOF'
#!/usr/bin/env python3
import psycopg2
import uuid
from datetime import datetime
from passlib.context import CryptContext

# RDS Configuration
DB_CONFIG = {
    'host': 'accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'accunode_admin',
    'password': 'AccuNode2024!SecurePass'
}

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=8)

def create_super_admin():
    print("👑 CREATING SUPER ADMIN IN RDS")
    print("=" * 40)
    
    # Super admin details
    user_id = str(uuid.uuid4())
    email = "admin@accunode.ai"
    username = "accunode"
    password = "SuperaAdmin123*"
    full_name = "accunode.ai"
    role = "super_admin"
    
    print(f"📋 Creating user: {email}")
    
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
            # Update existing user
            cur.execute("""
                UPDATE users 
                SET role = %s, hashed_password = %s, updated_at = %s, is_active = true
                WHERE email = %s
            """, (role, hashed_password, datetime.utcnow(), email))
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
            print("✅ Super admin created!")
        
        conn.commit()
        
        # Verify
        cur.execute("SELECT id, email, username, role, is_active FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        
        print(f"\n🎉 SUPER ADMIN VERIFIED:")
        print(f"   ID: {user[0]}")
        print(f"   Email: {user[1]}")
        print(f"   Username: {user[2]}")
        print(f"   Role: {user[3]}")
        print(f"   Active: {user[4]}")
        print(f"\n🔐 Credentials: {email} / {password}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    create_super_admin()
EOF

# Run the Python script
echo ""
echo "🏃 Running super admin creation script..."
python3 create_super_admin.py

# Test connection with psql
echo ""
echo "🧪 Testing database connection with psql..."
PGPASSWORD='AccuNode2024!SecurePass' psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -c "SELECT email, username, role FROM users WHERE role = 'super_admin';"

echo ""
echo "🎉 SETUP COMPLETE!"
echo "Super Admin Credentials:"
echo "   Email: admin@accunode.ai"
echo "   Password: SuperaAdmin123*"
echo "   Username: accunode"
