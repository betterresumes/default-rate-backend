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

