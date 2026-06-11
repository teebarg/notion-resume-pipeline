FROM beafdocker/notion-api-base:latest

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock* ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
