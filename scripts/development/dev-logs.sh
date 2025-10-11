#!/bin/bash
# View logs for AccuNode development services

set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo -e "${GREEN}📋 AccuNode Development Logs${NC}"
echo -e "=============================="

# Determine compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Check if any services are provided as arguments
if [ $# -eq 0 ]; then
    echo -e "${BLUE}Showing logs for all services (press Ctrl+C to exit):${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml logs -f
else
    echo -e "${BLUE}Showing logs for: $*${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml logs -f "$@"
fi
