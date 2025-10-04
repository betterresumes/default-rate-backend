#!/bin/bash
# Run tests in AccuNode development environment

set -e

echo "🧪 Running AccuNode Tests"
echo "========================="

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Determine compose command
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Ensure services are running
echo -e "${BLUE}Checking if development services are running...${NC}"
if ! $COMPOSE_CMD -f docker-compose.dev.yml ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  Development services are not running. Starting them...${NC}"
    ./scripts/dev-setup.sh
fi

# Run tests
echo -e "${BLUE}Running pytest in development container...${NC}"

if [ $# -eq 0 ]; then
    # Run all tests
    echo -e "${BLUE}Running all tests...${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml exec api pytest -v --cov=app tests/
else
    # Run specific tests
    echo -e "${BLUE}Running tests: $*${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml exec api pytest -v "$@"
fi

echo -e "${GREEN}✅ Tests completed${NC}"
