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
FROM beafdocker/notion-api-base:latest

COPY apps/api/pyproject.toml apps/api/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project


FROM base AS runtime

COPY --from=deps /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY apps/api .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]