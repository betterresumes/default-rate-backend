#!/bin/bash
# 🍎 macOS Database Access Script (No AWS costs)
# Works on your local macOS machine

set -e

echo "🍎 macOS Database Setup"
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
echo "   Database: postgres"
echo "   User: $DB_USER"

# Check if PostgreSQL client is installed
if ! command -v psql &> /dev/null; then
    echo "📦 PostgreSQL client not found. Installing via Homebrew..."
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "❌ Homebrew not found. Please install Homebrew first:"
        echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
    
    echo "Installing postgresql..."
    brew install postgresql
else
    echo "✅ PostgreSQL client already installed"
fi

# Check if Python packages are available
echo "🐍 Checking Python packages..."
python3 -c "import psycopg2" 2>/dev/null || pip3 install psycopg2-binary
python3 -c "import sqlalchemy" 2>/dev/null || pip3 install sqlalchemy
python3 -c "import pandas" 2>/dev/null || pip3 install pandas

# Create connection script
echo "🔗 Creating database connection script..."
cat > connect-rds.sh << 'EOF'
#!/bin/bash
# RDS Database Connection Script
export PGPASSWORD="AccuNode2024!SecurePass"
psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432
EOF

chmod +x connect-rds.sh

# Create table inspection script
cat > inspect-tables.sh << 'EOF'
#!/bin/bash
# Database Table Inspection Script
export PGPASSWORD="AccuNode2024!SecurePass"

echo "🔍 DATABASE TABLE INSPECTION"
echo "=========================================="

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
echo "🏗️ Database info:"
psql -h accunode-postgres.ck36iu4u6mpj.us-east-1.rds.amazonaws.com -U accunode_admin -d postgres -p 5432 -c "\l"

EOF

chmod +x inspect-tables.sh

# Test connection immediately
echo "🧪 Testing database connection..."
export PGPASSWORD="AccuNode2024!SecurePass"

# Test basic connection
if psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT -c "SELECT 'Connection successful!' as status;" 2>/dev/null; then
    echo "✅ Database connection successful!"
    
    echo ""
    echo "📋 Listing all tables in the database:"
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT -c "\dt" 2>/dev/null || echo "No tables found or permission denied"
    
    echo ""
    echo "📊 Database overview:"
    psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT -c "
    SELECT 
        current_database() as database_name,
        current_user as connected_as,
        version() as postgresql_version;
    " 2>/dev/null
    
else
    echo "❌ Database connection failed!"
    echo "This could be due to:"
    echo "1. Network connectivity issues"
    echo "2. RDS security group not allowing your IP"
    echo "3. Wrong credentials"
    echo "4. RDS instance not running"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Available Commands:"
echo "   ./connect-rds.sh        # Connect to RDS directly" 
echo "   ./inspect-tables.sh     # Quick table overview"
echo ""
echo "🔗 Manual connection:"
echo "   PGPASSWORD='AccuNode2024!SecurePass' psql -h $DB_HOST -U $DB_USER -d $DB_NAME -p $DB_PORT"
