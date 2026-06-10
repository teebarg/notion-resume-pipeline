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
FROM beafdocker/notion-api-base:latest

COPY apps/api/pyproject.toml apps/api/uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

COPY apps/api .

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
