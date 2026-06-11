# FROM python:3.12-slim

# ENV PYTHONUNBUFFERED=1
# ENV UV_COMPILE_BYTECODE=1
# ENV UV_LINK_MODE=copy

# # Install uv
# COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# WORKDIR /app

# ENV PATH="/app/.venv/bin:$PATH"

# COPY pyproject.toml uv.lock ./

# # Install dependencies first (better caching)
# RUN --mount=type=cache,target=/root/.cache/uv \
#     --mount=type=bind,source=uv.lock,target=uv.lock \
#     --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
#     uv sync --frozen --no-dev

# # Copy source code
# COPY ./app ./app

# # Install project
# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --frozen

# EXPOSE 8000


# syntax=docker/dockerfile:1.7

# FROM base AS runtime
# FROM beafdocker/notion-api-base:latest

# COPY apps/api/pyproject.toml apps/api/uv.lock ./

# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync

# COPY apps/api .

# ENV PATH="/app/.venv/bin:$PATH"

# EXPOSE 8000

# # CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]


# 1. Start directly from your custom base image that already has Playwright configured
FROM beafdocker/notion-api-base:latest

WORKDIR /app

# Streamline python environment outputs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/root/.cache/uv

# 2. Install uv quickly via its official standalone installer script
# This is much cleaner and faster than using standard pip
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:${PATH}"

# 3. Copy only your dependency definitions to maximize Docker layer caching
# COPY pyproject.toml uv.lock* ./
COPY apps/api/pyproject.toml apps/api/uv.lock* ./

# 4. Sync dependencies into the container's environment.
# Using the cache mount keeps restarts near-instant when your lockfile changes.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

EXPOSE 8000

# 5. Execute your application using hot-reloading
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
