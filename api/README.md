# Notion Resume API

FastAPI backend for the resume generation platform. Imports Notion pages, normalizes content into a canonical resume schema, and runs export jobs asynchronously via Redis.

## Structure

```text
app/
├── main.py              # Application factory & lifespan
├── config/              # Environment-based settings
├── core/                # Logging, Redis client
├── schemas/             # Pydantic v2 request/response models
├── services/            # Business logic
├── routers/             # Async HTTP endpoints
├── dependencies/        # FastAPI dependency injection
└── workers/             # ARQ background job workers
```

## Quick start

```bash
cd api
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -e ".[dev]"

cp .env.example .env
# Set NOTION_API_TOKEN and REDIS_URL

# Terminal 1 — API
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2 — background worker (requires Redis)
arq app.workers.settings.WorkerSettings
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| GET | `/health/ready` | Redis connectivity |
| POST | `/api/v1/notion/import` | Import resume from Notion page |
| GET | `/api/v1/resumes/templates` | List render templates |
| POST | `/api/v1/jobs/export` | Enqueue PDF/Markdown/HTML export |
| GET | `/api/v1/jobs/{job_id}` | Poll job status |

Interactive docs: http://localhost:8000/docs
