COMPOSE=docker compose

# ----------------------------
# Setup
# ----------------------------

setup:
	@echo "Installing root dependencies..."
	npm install

	@echo "Setting up environment..."
	cp .env.example .env || true

# ----------------------------
# Docker (Main Workflow)
# ----------------------------

up:
	@echo "Starting all services..."
	$(COMPOSE) up --build

down:
	@echo "Stopping all services..."
	$(COMPOSE) down

restart:
	@echo "Restarting services..."
	$(COMPOSE) down && $(COMPOSE) up --build

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

# ----------------------------
# Service-specific access
# ----------------------------

web:
	$(COMPOSE) up web

api:
	$(COMPOSE) up api

renderer:
	$(COMPOSE) up renderer

redis:
	$(COMPOSE) up redis

# ----------------------------
# Development (without full stack)
# ----------------------------

dev-web:
	cd apps/web && npm run dev

dev-api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

dev-renderer:
	cd services/renderer && node server.js

# ----------------------------
# Build
# ----------------------------

build:
	$(COMPOSE) build

rebuild:
	$(COMPOSE) build --no-cache

clean:
	@echo "Cleaning Docker system..."
	$(COMPOSE) down -v
	docker system prune -f

redis-cli:
	docker exec -it notion-resume-pipeline-redis-1 redis-cli


health:
	curl http://localhost:3000 || true
	curl http://localhost:8000/docs || true

help:
	@echo ""
	@echo "Available commands:"
	@echo "  make up           - start full system"
	@echo "  make down         - stop system"
	@echo "  make restart      - rebuild and restart"
	@echo "  make logs         - view logs"
	@echo "  make dev-web      - run frontend only"
	@echo "  make dev-api      - run backend only"
	@echo "  make clean        - cleanup docker system"
	@echo ""