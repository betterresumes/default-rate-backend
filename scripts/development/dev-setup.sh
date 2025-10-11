#!/bin/bash
# AccuNode Development Environment Setup Script
# This script sets up the local development environment using Docker

set -e

echo "🚀 Setting up AccuNode Local Development Environment"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Docker is installed and running
check_docker() {
    echo -e "${BLUE}Checking Docker installation...${NC}"
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker is not installed. Please install Docker Desktop first.${NC}"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo -e "${RED}❌ Docker is not running. Please start Docker Desktop.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker is installed and running${NC}"
}

# Check if Docker Compose is available
check_docker_compose() {
    echo -e "${BLUE}Checking Docker Compose...${NC}"
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        echo -e "${RED}❌ Docker Compose is not available.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ Docker Compose is available${NC}"
}

# Create environment file if it doesn't exist
setup_environment() {
    echo -e "${BLUE}Setting up environment files...${NC}"
    
    if [ ! -f .env.development ]; then
        echo -e "${YELLOW}⚠️  .env.development not found. Using default configuration.${NC}"
    else
        echo -e "${GREEN}✅ .env.development found${NC}"
    fi
    
    # Create .gitignore for development if it doesn't exist
    if [ ! -f .gitignore ]; then
        cat > .gitignore << EOF
# Development environment files
.env.development
.env.local

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.venv/

# Database
*.db
*.sqlite3

# IDE
.vscode/
.idea/
*.swp
*.swo

# Logs
*.log
logs/

# Docker
docker-compose.override.yml

# OS
.DS_Store
Thumbs.db
EOF
        echo -e "${GREEN}✅ Created .gitignore${NC}"
    fi
}

# Build and start services
start_services() {
    echo -e "${BLUE}Building and starting services...${NC}"
    
    # Use docker compose (newer) or docker-compose (legacy)
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    echo -e "${BLUE}Building development containers...${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml build --no-cache
    
    echo -e "${BLUE}Starting services in background...${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml up -d
    
    # Wait for services to be healthy
    echo -e "${BLUE}Waiting for services to be ready...${NC}"
    sleep 10
    
    # Check service health
    echo -e "${BLUE}Checking service status...${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml ps
}

# Run database migrations
setup_database() {
    echo -e "${BLUE}Setting up database...${NC}"
    
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    else
        COMPOSE_CMD="docker-compose"
    fi
    
    # Wait for database to be ready
    echo -e "${BLUE}Waiting for PostgreSQL to be ready...${NC}"
    $COMPOSE_CMD -f docker-compose.dev.yml exec -T postgres sh -c 'until pg_isready -U admin -d accunode_development; do sleep 1; done'
    
    # Run any database initialization if needed
    echo -e "${GREEN}✅ Database is ready${NC}"
    
    # Create tables (FastAPI will handle this on startup)
    echo -e "${BLUE}Creating database tables...${NC}"
    echo -e "${GREEN}✅ Database setup complete${NC}"
}

# Show connection information
show_info() {
    echo -e "\n${GREEN}🎉 Development environment is ready!${NC}"
    echo -e "======================================"
    echo -e ""
    echo -e "${BLUE}Services:${NC}"
    echo -e "  🌐 FastAPI Application: http://localhost:8000"
    echo -e "  📊 API Documentation: http://localhost:8000/docs"
    echo -e "  🗄️  PostgreSQL: localhost:5432"
    echo -e "  🔴 Redis: localhost:6379"
    echo -e "  ☁️  LocalStack (AWS): http://localhost:4566"
    echo -e ""
    echo -e "${BLUE}Database Connection:${NC}"
    echo -e "  Host: localhost"
    echo -e "  Port: 5432"
    echo -e "  Database: accunode_development"
    echo -e "  Username: admin"
    echo -e "  Password: dev_password_123"
    echo -e ""
    echo -e "${BLUE}Useful Commands:${NC}"
    echo -e "  📋 View logs: ./scripts/dev-logs.sh"
    echo -e "  🔄 Restart services: ./scripts/dev-restart.sh"
    echo -e "  🛑 Stop services: ./scripts/dev-stop.sh"
    echo -e "  🗄️  Connect to DB: ./scripts/dev-db.sh"
    echo -e "  🧪 Run tests: ./scripts/dev-test.sh"
    echo -e ""
    echo -e "${YELLOW}💡 Tip: Your code changes will be automatically reloaded!${NC}"
}

# Main execution
main() {
    echo -e "${BLUE}Starting AccuNode development setup...${NC}"
    
    check_docker
    check_docker_compose
    setup_environment
    start_services
    setup_database
    show_info
    
    echo -e "\n${GREEN}✅ Setup complete! Happy coding! 🚀${NC}"
}

# Run main function
main
