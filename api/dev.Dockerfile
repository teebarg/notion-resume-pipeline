# FROM beafdocker/notion-api-base:latest

# WORKDIR /app

# COPY pyproject.toml uv.lock* ./

# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --frozen --no-install-project

# EXPOSE 8000

# CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Fix: Added "-bookworm" to the slim tag name
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

WORKDIR /app

# Install system utilities needed for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

# Sync ALL dependencies (including dev tools)
RUN uv sync --frozen

# Automatically fetch OS dependencies AND browser binaries for Chromium
RUN uv run playwright install-deps chromium
RUN uv run playwright install chromium

COPY . .
EXPOSE 8000

# Run with uv and enable live code reloading
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


