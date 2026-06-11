# # =========================================
# # Stage 1 — Builder
# # =========================================
# FROM python:3.12-slim AS builder

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# # Install system deps
# RUN apt-get update && apt-get install -y \
#     curl \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# # Install uv
# RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# ENV PATH="/root/.local/bin:$PATH"

# COPY pyproject.toml uv.lock ./

# # Create virtual environment
# RUN uv venv /opt/venv

# ENV PATH="/opt/venv/bin:$PATH"

# # Install dependencies
# RUN uv sync --frozen --no-dev

# COPY app ./app

# RUN uv pip install .

# # =========================================
# # Stage 2 — Runtime
# # =========================================
# FROM python:3.12-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# # Copy virtual environment from builder
# COPY --from=builder /opt/venv /opt/venv

# ENV PATH="/opt/venv/bin:$PATH"

# COPY app ./app

# EXPOSE 8000

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# syntax=docker/dockerfile:1.7

# FROM base AS deps
# FROM beafdocker/notion-api-base:latest

# COPY apps/api/pyproject.toml apps/api/uv.lock ./

# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --frozen --no-install-project


# FROM base AS runtime

# COPY --from=deps /app/.venv /app/.venv
# ENV PATH="/app/.venv/bin:$PATH"

# WORKDIR /app

# COPY apps/api .

# EXPOSE 8000

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# ==============================================================================
# STAGE 1: The Builder (Compiles dependencies safely)
# ==============================================================================
FROM beafdocker/notion-api-base:latest AS builder

WORKDIR /app

ENV UV_CACHE_DIR=/root/.cache/uv

# Install uv using the official standalone script
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:${PATH}"

COPY apps/api/pyproject.toml apps/api/uv.lock* ./

# Sync dependencies into a self-contained virtual environment.
# We pass --no-dev to strip out any testing or linting utilities.
RUN uv sync --frozen --no-dev --no-install-project

# ==============================================================================
# STAGE 2: The Runtime (Ultra-lean, secure, non-root)
# ==============================================================================
FROM beafdocker/notion-api-base:latest AS runner

WORKDIR /app

# Production optimization flags
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENV=production
# Force python to favor our isolated virtual env binaries
ENV PATH="/app/.venv/bin:$PATH"

# 1. Create a dedicated, non-privileged system user for execution
RUN addgroup --system fastapi && \
    adduser --system --ingroup fastapi appuser

# 2. Copy the compiled virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# 3. Copy only the production application code
COPY ./apps/api/app /app/app

# 4. Set secure permissions so the non-root user owns the workspace
RUN chown -R appuser:fastapi /app

# Drop root privileges completely
USER appuser

EXPOSE 8000

# 5. Run with optimal production workers, NO reload flag, and direct gunicorn/uvicorn workers
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]