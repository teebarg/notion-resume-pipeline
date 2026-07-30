# FROM beafdocker/notion-api-base:latest AS builder

# WORKDIR /app

# COPY api/pyproject.toml api/uv.lock* ./

# # We pass --no-dev to strip out any testing or linting utilities.
# RUN uv sync --frozen --no-dev --no-install-project

# # ---------- STAGE 2: Final Runtime ----------
# FROM beafdocker/notion-api-base:latest AS runtime
# WORKDIR /app

# # Copy the virtualenv from builder (only compiled packages)
# COPY --from=builder /app/.venv /app/.venv
# ENV PATH="/app/.venv/bin:$PATH"
# ENV PYTHONPATH=/app

# COPY ./app /app/app

# CMD ["uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT"]


# ==========================================
# STAGE 1: Builder (Creates the virtualenv)
# ==========================================
FROM ghcr.io/astral-sh/uv:latest AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
# Install production-only dependencies into /app/.venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ==========================================
# STAGE 2: Runner (Lightweight Runtime)
# ==========================================
FROM python:3.11-slim AS runner
# Install critical system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxcomposite1 libxdamage1 libxfixes1 libxrandr2 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 libgtk-3-0 \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*
WORKDIR /app
# Copy the pre-built virtual environment from builder stage
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
# Install ONLY the Chromium browser binary
RUN playwright install chromium
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
