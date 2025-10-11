#!/bin/bash
# Restart AccuNode development services

set -e

echo "🔄 Restarting AccuNode Development Services"
echo "==========================================="

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Determine compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

if [ $# -eq 0 ]; then
    echo -e "${BLUE}Restarting all services...${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml restart
else
    echo -e "${BLUE}Restarting services: $*${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml restart "$@"
fi

echo -e "${GREEN}✅ Services restarted${NC}"

# Show status
echo -e "${BLUE}Current status:${NC}"
$COMPOSE_CMD -f docker-compose.dev.yml ps
