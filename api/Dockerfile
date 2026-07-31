# Stage 1: Build environment
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Compile Python bytecode for faster startups and optimize file links
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install system dependencies required for building packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev --no-editable

# Stage 2: Clean production runtime
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS runtime

WORKDIR /app

# Copy the lightweight pre-built virtual environment
COPY --from=builder /app/.venv /app/.venv

# Force Python to use the virtual environment binaries directly
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN uv run playwright install-deps chromium
RUN uv run playwright install chromium

COPY ./app /app/app

EXPOSE 10000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
