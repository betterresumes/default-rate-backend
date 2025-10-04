#!/bin/bash
# 🆓 FREE AWS CloudShell Database Access Script
# No EC2 costs - uses AWS CloudShell (completely free)

set -e

echo "🌩️  AWS CloudShell Database Setup (FREE)"
echo "=" * 50

# Database connection details
DB_HOST="accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com"
DB_PORT="5432"
DB_NAME="postgres"
DB_USER="accunode_admin"
DB_PASSWORD="AccuNode2024!SecurePass"

echo "📋 Database Connection Info:"
echo "   Host: $DB_HOST"
echo "   Port: $DB_PORT"
echo "   Database: $DB_NAME"
echo "   User: $DB_USER"

# Install PostgreSQL client
echo "📦 Installing PostgreSQL client..."
sudo yum install -y postgresql15

# Install Python and required packages
echo "🐍 Installing Python packages..."
sudo yum install -y python3 python3-pip
pip3 install --user psycopg2-binary sqlalchemy pandas

# Create connection script
echo "🔗 Creating database connection script..."
cat > ~/connect-rds.sh << 'EOF'
#!/bin/bash
# RDS Database Connection Script
export PGPASSWORD="AccuNode2024!SecurePass"
psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432
EOF

chmod +x ~/connect-rds.sh

# Create table inspection script
cat > ~/inspect-tables.sh << 'EOF'
#!/bin/bash
# Database Table Inspection Script
export PGPASSWORD="AccuNode2024!SecurePass"

echo "🔍 DATABASE TABLE INSPECTION"
echo "=" * 40

echo "📋 List of all tables:"
psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432 -c "\dt"

echo ""
echo "📊 Table row counts:"
psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432 -c "
SELECT 
    schemaname,
    tablename, 
    n_tup_ins - n_tup_del as row_count
FROM pg_stat_user_tables 
ORDER BY row_count DESC;
"

echo ""
echo "🏗️ Database schema info:"
psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432 -c "\l"

EOF

chmod +x ~/inspect-tables.sh

# Create Python database inspector
cat > ~/db_inspector.py << 'EOF'
#!/usr/bin/env python3
"""
RDS Database Inspector - Run from AWS CloudShell
"""

import psycopg2
import sys
from datetime import datetime

# Database connection
DB_CONFIG = {
    'host': 'accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com',
    'port': 5432,
    'database': 'postgres',
    'user': 'accunode_admin',
    'password': 'AccuNode2024!SecurePass'
}

def connect_db():
    """Connect to the database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

def inspect_database():
    """Inspect database structure"""
    conn = connect_db()
    cur = conn.cursor()
    
    print("🔍 RDS DATABASE INSPECTION")
    print("=" * 50)
    
    # List all tables
    print("\n📋 All Tables:")
    cur.execute("""
        SELECT schemaname, tablename, tableowner 
        FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)
    
    tables = cur.fetchall()
    if tables:
        print(f"{'Schema':<10} {'Table Name':<30} {'Owner':<15}")
        print("-" * 55)
        for schema, table, owner in tables:
            print(f"{schema:<10} {table:<30} {owner:<15}")
    else:
        print("No user tables found.")
    
    # Table sizes and row counts
    print(f"\n📊 Table Statistics:")
    cur.execute("""
        SELECT 
            schemaname,
            tablename,
            n_tup_ins - n_tup_del as estimated_rows,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_stat_user_tables 
        ORDER BY n_tup_ins - n_tup_del DESC;
    """)
    
    stats = cur.fetchall()
    if stats:
        print(f"{'Schema':<10} {'Table':<25} {'Rows':<15} {'Size':<10}")
        print("-" * 65)
        for schema, table, rows, size in stats:
            print(f"{schema:<10} {table:<25} {rows or 0:<15} {size:<10}")
    else:
        print("No table statistics available.")
    
    # Database info
    print(f"\n🗄️ Database Information:")
    cur.execute("SELECT version();")
    version = cur.fetchone()[0]
    print(f"PostgreSQL Version: {version}")
    
    cur.execute("SELECT current_database(), current_user, inet_server_addr(), inet_server_port();")
    db_info = cur.fetchone()
    print(f"Database: {db_info[0]}")
    print(f"Current User: {db_info[1]}")
    print(f"Server: {db_info[2]}:{db_info[3]}")
    
    # Recent activity (if any)
    print(f"\n⏰ Database Activity:")
    cur.execute("""
        SELECT 
            schemaname,
            tablename,
            n_tup_ins as inserts,
            n_tup_upd as updates,
            n_tup_del as deletes
        FROM pg_stat_user_tables 
        WHERE n_tup_ins + n_tup_upd + n_tup_del > 0
        ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC;
    """)
    
    activity = cur.fetchall()
    if activity:
        print(f"{'Table':<25} {'Inserts':<10} {'Updates':<10} {'Deletes':<10}")
        print("-" * 55)
        for schema, table, inserts, updates, deletes in activity:
            print(f"{table:<25} {inserts:<10} {updates:<10} {deletes:<10}")
    else:
        print("No activity recorded yet.")
    
    conn.close()

if __name__ == "__main__":
    inspect_database()
EOF

chmod +x ~/db_inspector.py

echo "✅ Setup complete!"
echo ""
echo "🎯 Available Commands:"
echo "   ~/connect-rds.sh        # Connect to RDS directly"
echo "   ~/inspect-tables.sh     # Quick table overview"
echo "   python3 ~/db_inspector.py  # Detailed Python inspection"
echo ""
echo "🔗 Direct psql connection:"
echo "   PGPASSWORD='AccuNode2024!SecurePass' psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT"
echo ""
echo "📝 Test connection:"
echo "   ~/connect-rds.sh"
