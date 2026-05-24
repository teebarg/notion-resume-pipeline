# FROM python:3.12-slim

# ENV PYTHONDONTWRITEBYTECODE=1
# ENV PYTHONUNBUFFERED=1

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     curl \
#     build-essential \
#     && rm -rf /var/lib/apt/lists/*

# RUN curl -LsSf https://astral.sh/uv/install.sh | sh
# ENV PATH="/root/.local/bin:$PATH"

# COPY pyproject.toml uv.lock ./
# COPY README.md ./

# # Install all deps including dev extras
# RUN uv sync --frozen

# ENV PATH="/app/.venv/bin:$PATH"

# # Source is mounted as a volume — editable install picks up live changes
# RUN uv pip install -e .

# EXPOSE 8000

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# FROM python:3.11-slim

# # Install uv
# COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# ENV PYTHONDONTWRITEBYTECODE=1 \
#     PYTHONUNBUFFERED=1 \
#     UV_PROJECT_ENVIRONMENT=/venv \
#     PATH="/venv/bin:$PATH"

# WORKDIR /app

# RUN apt-get update && apt-get install -y \
#     curl \
#     build-essential \
#     ca-certificates \
#     && rm -rf /var/lib/apt/lists/*

# COPY pyproject.toml uv.lock ./

# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync --frozen

# COPY . .

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]


FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

WORKDIR /app

ENV PATH="/app/.venv/bin:$PATH"

# Install dependencies first (better caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-dev

# Copy source code
COPY ./app ./app

# Install project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen

EXPOSE 8000

CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]