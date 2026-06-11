FROM beafdocker/notion-api-base:latest AS builder

WORKDIR /app

COPY apps/api/pyproject.toml apps/api/uv.lock* ./

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

# Create a dedicated system user for execution
RUN addgroup --system fastapi && \
    adduser --system --ingroup fastapi appuser

COPY --from=builder /app/.venv /app/.venv

COPY ./apps/api/app /app/app

# Set secure permissions so the non-root user owns the workspace
RUN chown -R appuser:fastapi /app

# Drop root privileges completely
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]