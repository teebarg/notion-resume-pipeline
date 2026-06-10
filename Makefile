# Variables
COMPOSE := docker compose
DOCKER_USER := beafdocker

API_BASE := $(DOCKER_USER)/notion-api-base
API_IMAGE := $(DOCKER_USER)/notion-api
WEB_IMAGE := $(DOCKER_USER)/notion-web

VERSION ?= latest
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

.PHONY: dev-web dev-api shell-dev fctx bctx previews help \
        dev dev-build restart stop logs api-logs web-logs \
        shell-api shell-web test build-base build-api push-api release clean

# ----------------------------
# Development (shell)
# ----------------------------

dev-web:
	cd apps/web && npm run dev

dev-api:
	cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000

shell-dev:
	npx concurrently \
		"cd apps/api && .venv/bin/uvicorn app.main:app --reload --port 8000" \
		"cd apps/web && npm run dev"

# ----------------------------
# Context for AI
# ----------------------------
fctx:
	cd apps/web && npx repomix

bctx:
	cd apps/api && npx repomix

# ----------------------------
# Scripts
# ----------------------------
previews:
	@echo "Re-generating template asset blueprints..."
	cd apps/api && .venv/bin/python scripts/generate_previews.py $(if $(TEMPLATE),--template $(TEMPLATE))


# -------------------------
# DEV / DOCKER COMPOSE
# -------------------------
dev:
	$(COMPOSE) up

dev-build:
	$(COMPOSE) up --build

restart:
	@echo "Restarting services..."
	$(COMPOSE) down && $(COMPOSE) up --build

stop:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

api-logs:
	$(COMPOSE) logs -f api

web-logs:
	$(COMPOSE) logs -f web

# -------------------------
# SHELL ACCESS
# -------------------------
shell-api:
	$(COMPOSE) exec api bash

shell-web:
	$(COMPOSE) exec web sh

# -------------------------
# TEST
# -------------------------
test:
	$(COMPOSE) exec api pytest

# -------------------------
# BUILD (VERSIONED)
# -------------------------
build-base:
	docker build \
		-f infra/docker/base.api.Dockerfile \
		-t $(API_BASE):latest \
		.

build-api:
	docker build \
		-f infra/docker/api.Dockerfile \
		-t $(API_IMAGE):latest \
		-t $(API_IMAGE):$(VERSION) \
		-t $(API_IMAGE):$(GIT_SHA) \
		.

# -------------------------
# PUSH
# -------------------------
push-api:
	docker push $(API_IMAGE):latest
	docker push $(API_IMAGE):$(VERSION)
	docker push $(API_IMAGE):$(GIT_SHA)

# -------------------------
# RELEASE
# -------------------------
release: build-base build-api push-api

# -------------------------
# CLEAN
# -------------------------
clean:
	@echo "Cleaning Docker system..."
	$(COMPOSE) down -v
	docker system prune -f