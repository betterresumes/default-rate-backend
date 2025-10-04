# AccuNode Development Makefile
# Simple commands for local development

.PHONY: help setup start stop restart logs db test clean

# Colors for help output
BLUE=\033[0;34m
GREEN=\033[0;32m
YELLOW=\033[1;33m
NC=\033[0m # No Color

help: ## Show this help message
	@echo -e "$(GREEN)🚀 AccuNode Development Commands$(NC)"
	@echo -e "=================================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "$(YELLOW)💡 Tip: Use 'make setup' for first-time setup$(NC)"

setup: ## 🛠️  Initial setup of development environment
	@echo -e "$(BLUE)Setting up development environment...$(NC)"
	./scripts/local/dev-setup.sh

start: ## 🚀 Start all development services
	@echo -e "$(BLUE)Starting development services...$(NC)"
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml up -d; \
	else \
		docker-compose -f docker-compose.dev.yml up -d; \
	fi
	@echo -e "$(GREEN)✅ Services started. API: http://localhost:8000$(NC)"

stop: ## 🛑 Stop all development services
	@echo -e "$(BLUE)Stopping development services...$(NC)"
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml down; \
	else \
		docker-compose -f docker-compose.dev.yml down; \
	fi
	@echo -e "$(GREEN)✅ Services stopped$(NC)"

restart: ## 🔄 Restart all development services
	@echo -e "$(BLUE)Restarting development services...$(NC)"
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml restart; \
	else \
		docker-compose -f docker-compose.dev.yml restart; \
	fi
	@echo -e "$(GREEN)✅ Services restarted$(NC)"

logs: ## 📋 View logs from all services
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml logs -f; \
	else \
		docker-compose -f docker-compose.dev.yml logs -f; \
	fi

logs-api: ## 📋 View API logs only
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml logs -f api; \
	else \
		docker-compose -f docker-compose.dev.yml logs -f api; \
	fi

logs-db: ## 📋 View database logs only
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml logs -f postgres; \
	else \
		docker-compose -f docker-compose.dev.yml logs -f postgres; \
	fi

db: ## 🗄️  Connect to development database
	./scripts/local/dev-db.sh

test: ## 🧪 Run all tests
	./scripts/local/dev-test.sh

init-local: ## 🏠 Initialize local development with sample data
	@echo -e "$(BLUE)Setting up local development environment...$(NC)"
	python3 scripts/local/complete_local_setup.py
	@echo -e "$(GREEN)✅ Local environment ready! API: http://localhost:8000/docs$(NC)"

test-watch: ## 🧪 Run tests in watch mode
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml exec api pytest --watch; \
	else \
		docker-compose -f docker-compose.dev.yml exec api pytest --watch; \
	fi

build: ## 🔨 Rebuild development containers
	@echo -e "$(BLUE)Rebuilding development containers...$(NC)"
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml build --no-cache; \
	else \
		docker-compose -f docker-compose.dev.yml build --no-cache; \
	fi
	@echo -e "$(GREEN)✅ Containers rebuilt$(NC)"

shell: ## 🐚 Open shell in API container
	@if docker compose version >/dev/null 2>&1; then \
		docker compose -f docker-compose.dev.yml exec api bash; \
	else \
		docker-compose -f docker-compose.dev.yml exec api bash; \
	fi

shell-db: ## 🐚 Open shell in database container
	docker-compose -f docker-compose.dev.yml exec postgres bash

status: ## 📊 Show status of all services
	docker-compose -f docker-compose.dev.yml ps

clean: ## 🧹 Clean up containers and volumes
	@echo -e "$(BLUE)Cleaning up development environment...$(NC)"
	docker-compose -f docker-compose.dev.yml down -v
	docker system prune -f
	@echo -e "$(GREEN)✅ Cleanup completed$(NC)"

clean-all: ## 🧹 Clean everything including images
	@echo -e "$(BLUE)Cleaning up everything...$(NC)"
	docker-compose -f docker-compose.dev.yml down -v --rmi all
	docker system prune -af
	@echo -e "$(GREEN)✅ Complete cleanup done$(NC)"

# Development workflow helpers
dev-setup: setup ## Alias for setup
dev-start: start ## Alias for start
dev-stop: stop ## Alias for stop

# Quick access to docs
docs: ## 📖 Open development documentation
	@echo -e "$(GREEN)📖 Development Documentation:$(NC)"
	@echo -e "  Local Setup: docs/LOCAL_DEVELOPMENT_GUIDE.md"
	@echo -e "  Team Guide: docs/team/TEAM_ONBOARDING_GUIDE.md"
	@echo -e "  API Docs: http://localhost:8000/docs"

# Production deployment helpers
deploy-check: ## ✅ Check if ready for production deployment
	@echo -e "$(BLUE)Checking deployment readiness...$(NC)"
	@./scripts/local/dev-test.sh
	@echo -e "$(GREEN)✅ Tests passed - ready for production!$(NC)"
	@echo -e "$(YELLOW)💡 Next steps:$(NC)"
	@echo -e "  1. git checkout prod"
	@echo -e "  2. git merge prod-dev"
	@echo -e "  3. git push origin prod"

# Default target
.DEFAULT_GOAL := help
