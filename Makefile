PROJECT_SLUG = resume-pipeline
DOCKER_HUB := beafdocker
COMPOSE := docker compose

API_BASE := $(DOCKER_HUB)/notion-api-base
API_IMAGE := $(DOCKER_HUB)/notion-api

VERSION ?= latest
GIT_SHA := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

.PHONY: previews build-base build-api push-api release

# ----------------------------
# Repomix Source Context for AI
# ----------------------------
.PHONY: fctx bctx ctx-all
fctx:
	@cd apps/web && npx repomix

bctx:
	@cd apps/api && npx repomix

ctx-all: fctx bctx

# ----------------------------
# Scripts
# ----------------------------
previews:
	@echo "Re-generating template asset blueprints..."
	cd apps/api && .venv/bin/python scripts/generate_previews.py $(if $(TEMPLATE),--template $(TEMPLATE))


# -------------------------
# DEV / DOCKER COMPOSE
# -------------------------
.PHONY: build
build:
	$(COMPOSE) -p $(PROJECT_SLUG) build

.PHONY: build-no-cache
build-no-cache:
	$(COMPOSE) -p $(PROJECT_SLUG) build --no-cache

.PHONY: up
up:
	$(COMPOSE) -p $(PROJECT_SLUG) up --build

.PHONY: update
update:
	$(COMPOSE) -p $(PROJECT_SLUG) up -d --force-recreate $(s)

.PHONY: update-all
update-all:
	$(COMPOSE) -p $(PROJECT_SLUG) up -d --force-recreate

.PHONY: prod-test
prod-test:
	$(COMPOSE) -p $(PROJECT_SLUG) --profile test up --build

.PHONY: stop
stop:
	$(COMPOSE) -p $(PROJECT_SLUG) down

# ==========================================
# Debugging
# ==========================================
.PHONY: logs
logs:
	$(COMPOSE) -p $(PROJECT_SLUG) logs -f $(s)

.PHONY: shell-web
shell-web:
	$(COMPOSE) -p $(PROJECT_SLUG) exec web sh

.PHONY: shell-api
shell-api:
	$(COMPOSE) -p $(PROJECT_SLUG) exec api /bin/bash

.PHONY: install
install:
	$(COMPOSE) -p $(PROJECT_SLUG) exec api uv pip install $(package)

.PHONY: prep
prep:
	$(COMPOSE) -p $(PROJECT_SLUG) exec api ./scripts/prestart.sh

.PHONY: lint-backend
lint-backend:
	$(COMPOSE) -p $(PROJECT_SLUG) exec api ./scripts/lint.sh

.PHONY: test-backend
test-backend:
	$(COMPOSE) -p $(PROJECT_SLUG) exec api pytest

.PHONY: uv-lock
uv-lock:
	$(COMPOSE) -p $(PROJECT_SLUG) exec $(s) uv lock --check

# -------------------------
# BUILD (VERSIONED)
# -------------------------
build-base:
	docker build --platform=linux/amd64 \
		-f apps/api/base.Dockerfile \
		-t $(API_BASE):latest \
		.

build-api:
	docker build --platform=linux/amd64 \
		-f apps/api/Dockerfile \
		-t $(API_IMAGE):latest \
		-t $(API_IMAGE):$(VERSION) \
		-t $(API_IMAGE):$(GIT_SHA) \
		.
		
push-api:
	docker push $(API_IMAGE):latest
	docker push $(API_IMAGE):$(VERSION)
	docker push $(API_IMAGE):$(GIT_SHA)

# -------------------------
# RELEASE
# -------------------------
release: build-base build-api push-api
