#!/bin/bash
# Stop AccuNode development services

set -e

echo "🛑 Stopping AccuNode Development Services"
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo -e "${BLUE}Stopping development services...${NC}"
$COMPOSE_CMD -f docker-compose.dev.yml down

echo -e "${GREEN}✅ All development services stopped${NC}"

# Optionally remove volumes (uncomment if you want to reset data)
# echo -e "${BLUE}Removing development volumes...${NC}"
# $COMPOSE_CMD -f docker-compose.dev.yml down -v
# echo -e "${GREEN}✅ Development volumes removed${NC}"
