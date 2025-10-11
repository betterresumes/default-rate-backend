#!/bin/bash
# Connect to AccuNode development database

set -e

echo "🗄️ Connecting to AccuNode Development Database"
echo "=============================================="

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Database connection details
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="accunode_development"
DB_USER="admin"
DB_PASSWORD="dev_password_123"

echo -e "${BLUE}Database Connection Details:${NC}"
echo -e "  Host: $DB_HOST"
echo -e "  Port: $DB_PORT"
echo -e "  Database: $DB_NAME"
echo -e "  Username: $DB_USER"
echo -e ""

# Check if pgcli is available (better PostgreSQL CLI)
if command -v pgcli &> /dev/null; then
    echo -e "${GREEN}Using pgcli for enhanced database experience...${NC}"
    PGPASSWORD=$DB_PASSWORD pgcli -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME
elif command -v psql &> /dev/null; then
    echo -e "${GREEN}Using psql for database connection...${NC}"
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME
else
    echo -e "${YELLOW}⚠️  Neither pgcli nor psql found locally.${NC}"
    echo -e "${BLUE}Connecting via Docker container...${NC}"
    
    # Determine compose command
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    $COMPOSE_CMD -f docker-compose.dev.yml exec postgres psql -U $DB_USER -d $DB_NAME
fi
