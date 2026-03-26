# AI Platform Makefile
# Complete setup and management commands

.PHONY: help setup start stop restart logs clean build status

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)AI Platform - Available Commands$(NC)"
	@echo "========================================"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "$(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

setup: ## Initial setup - install dependencies and configure
	@echo "$(BLUE)Setting up AI Platform...$(NC)"
	@mkdir -p logs models shared data
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Creating .env from template...$(NC)"; \
		cp .env.example .env 2>/dev/null || echo "$(RED)Please create .env file manually$(NC)"; \
	fi
	@echo "$(GREEN)Setup complete!$(NC)"
	@echo "$(YELLOW)Next: Run 'make build' to build containers, then 'make start'$(NC)"

build: ## Build all Docker containers
	@echo "$(BLUE)Building AI Platform containers...$(NC)"
	docker-compose build --parallel
	@echo "$(GREEN)Build complete!$(NC)"

start: ## Start all services
	@echo "$(BLUE)Starting AI Platform...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)AI Platform is starting up!$(NC)"
	@echo "$(YELLOW)Waiting for services to be ready...$(NC)"
	@sleep 10
	@$(MAKE) status

stop: ## Stop all services
	@echo "$(BLUE)Stopping AI Platform...$(NC)"
	docker-compose down
	@echo "$(GREEN)AI Platform stopped.$(NC)"

restart: ## Restart all services
	@echo "$(BLUE)Restarting AI Platform...$(NC)"
	docker-compose restart
	@echo "$(GREEN)Restart complete!$(NC)"

logs: ## View logs from all services
	docker-compose logs -f --tail=100

logs-%: ## View logs from specific service (e.g., make logs-orchestrator)
	docker-compose logs -f --tail=100 $*

status: ## Check status of all services
	@echo "$(BLUE)AI Platform Service Status:$(NC)"
	@echo "========================================"
	@docker-compose ps
	@echo ""
	@echo "$(GREEN)Access Points:$(NC)"
	@echo "  - API/Orchestrator: http://localhost:8000"
	@echo "  - Grafana:          http://localhost:3000"
	@echo "  - Prometheus:       http://localhost:9090"
	@echo "  - MinIO Console:    http://localhost:9001"
	@echo "  - Vault UI:         http://localhost:8200"
	@echo "  - Nginx Proxy:      http://localhost:80"

clean: ## Stop and remove all containers, volumes, and data
	@echo "$(RED)WARNING: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	docker-compose down -v
	docker system prune -f
	@echo "$(GREEN)Cleanup complete!$(NC)"

update: ## Pull latest images and rebuild
	@echo "$(BLUE)Updating AI Platform...$(NC)"
	docker-compose pull
	docker-compose build --no-cache
	@echo "$(GREEN)Update complete! Run 'make restart' to apply changes.$(NC)"

shell-%: ## Open shell in specific service container (e.g., make shell-orchestrator)
	docker-compose exec $* /bin/bash

exec-%: ## Execute command in specific service (e.g., make exec-orchestrator python -c "print('hello')")
	docker-compose exec $* $(filter-out $@,$(MAKECMDGOALS))

test: ## Run health checks on all services
	@echo "$(BLUE)Running health checks...$(NC)"
	@curl -s http://localhost:8000/health && echo " ✓ Orchestrator"
	@curl -s http://localhost:8001/health && echo " ✓ AI Agent"
	@curl -s http://localhost:8002/health && echo " ✓ Data Agent"
	@curl -s http://localhost:8003/health && echo " ✓ DevOps Agent"
	@curl -s http://localhost:8004/health && echo " ✓ NetMon Agent"
	@curl -s http://localhost:8005/health && echo " ✓ Security Agent"
	@echo "$(GREEN)All services healthy!$(NC)"

install-ollama-model: ## Install a model in Ollama (e.g., make install-ollama-model MODEL=llama2)
	@echo "$(BLUE)Installing Ollama model: $(MODEL)$(NC)"
	docker-compose exec ollama ollama pull $(MODEL)
	@echo "$(GREEN)Model $(MODEL) installed!$(NC)"

backup: ## Backup all persistent data
	@echo "$(BLUE)Creating backup...$(NC)"
	@mkdir -p backups
	docker-compose exec postgres pg_dump -U postgres aipm > backups/postgres_$(shell date +%Y%m%d_%H%M%S).sql
	docker run --rm -v ai-platform_redis-data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/redis_$(shell date +%Y%m%d_%H%M%S).tar.gz -C /data .
	@echo "$(GREEN)Backup complete! Files in ./backups/$(NC)"

# Development helpers
dev-setup: setup ## Setup development environment with hot-reload
	@echo "$(BLUE)Setting up development environment...$(NC)"
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

lint: ## Run linters on Python code
	@echo "$(BLUE)Running linters...$(NC)"
	@cd services/orchestrator && python -m flake8 . || true
	@echo "$(YELLOW)Linting complete (warnings shown above)$(NC)"

# Prevent make from interpreting extra arguments as targets
%:
	@:
