PROJECT_SLUG = resume-pipeline
DOCKER_HUB := beafdocker

API_BASE := $(DOCKER_HUB)/notion-api-base
API_IMAGE := $(DOCKER_HUB)/notion-api

IMAGE_TAG := $(if $(shell git rev-parse --short HEAD 2>NUL),$(shell git rev-parse --short HEAD 2>NUL),latest)
DOCKER_COMPOSE = docker compose -p $(PROJECT_SLUG)

.PHONY: previews build-api push-api release

# ----------------------------
# Repomix Source Context for AI
# ----------------------------
.PHONY: fctx bctx ctx-all
fctx:
	@cd web && npx repomix

bctx:
	@cd api && npx repomix

ctx-all: fctx bctx

# ----------------------------
# Scripts
# ----------------------------
previews:
	@echo "Re-generating template asset blueprints..."
	cd api && .venv/bin/python scripts/generate_previews.py $(if $(TEMPLATE),--template $(TEMPLATE))


# -------------------------
# DEV / DOCKER COMPOSE
# -------------------------
.PHONY: build
build:
	$(DOCKER_COMPOSE) build

.PHONY: build-no-cache
build-no-cache:
	$(DOCKER_COMPOSE) build --no-cache

.PHONY: up
up:
	$(DOCKER_COMPOSE) up

.PHONY: update
update:
	$(DOCKER_COMPOSE) up -d --force-recreate $(s)

.PHONY: update-all
update-all:
	$(DOCKER_COMPOSE) up -d --force-recreate

.PHONY: prod-test
prod-test:
	$(DOCKER_COMPOSE) --profile test up --build

.PHONY: stop
stop:
	$(DOCKER_COMPOSE) down

# ==========================================
# Debugging
# ==========================================
.PHONY: logs
logs:
	$(DOCKER_COMPOSE) logs -f $(s)

.PHONY: shell-web
shell-web:
	$(DOCKER_COMPOSE) exec web sh

.PHONY: shell-api
shell-api:
	$(DOCKER_COMPOSE) exec api /bin/bash

.PHONY: install
install:
	$(DOCKER_COMPOSE) exec api uv pip install $(package)

.PHONY: prep
prep:
	$(DOCKER_COMPOSE) exec api ./scripts/prestart.sh

.PHONY: lint-backend
lint-backend:
	$(DOCKER_COMPOSE) exec api ./scripts/lint.sh

.PHONY: test-backend
test-backend:
	$(DOCKER_COMPOSE) exec api pytest

.PHONY: uv-lock
uv-lock:
	$(DOCKER_COMPOSE) exec $(s) uv lock --check

# -------------------------
# BUILD (VERSIONED)
# -------------------------
build-api:
	docker build --platform=linux/amd64 \
		-f api/Dockerfile \
		-t $(API_IMAGE):latest \
		-t $(API_IMAGE):$(IMAGE_TAG) \
		./api

.PHONY: run-api-local
run-api-local:
	docker run --rm -it \
		--platform linux/amd64 \
		--network dev-net \
		-p 8000:8000 \
		--env-file api/.env \
		$(API_IMAGE):$(IMAGE_TAG) \

push-api:
	docker push $(API_IMAGE):latest
	docker push $(API_IMAGE):$(IMAGE_TAG)
