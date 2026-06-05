# Notion Resume Pipeline

Import structured resume data from Notion and export beautiful, production-ready resumes as PDF, Markdown, or JSON.

A developer-first resume rendering platform built as a document pipeline — not a drag-and-drop resume builder. The FastAPI backend is the single source of truth for parsing, normalization, and HTML rendering.

## Features

- Import from Notion
- Canonical normalization pipeline (`ResumeData` schema)
- Multiple server-rendered HTML/CSS templates
- Live preview via backend iframe routes
- Playwright PDF generation
- Markdown export (client-side, from normalized data)
- JSON export (client-side, from normalized data)
- Backend-driven rendering
- Responsive Next.js UI
- Docker development environment

## Architecture

```text
Notion
  ↓
FastAPI Import
  ↓
Normalization (parser → mapper)
  ↓
ResumeData Schema
  ↓
Template Renderer (Jinja2 HTML/CSS)
  ↓
Preview / PDF / Markdown / JSON
```

**Preview flow**

```text
GET /api/v1/notion/preview/{page_id}?template={template_id}&variant={variant_id}
```

The same HTML pipeline powers both live preview and PDF export.

## Tech Stack

**Frontend**

- Next.js
- React
- TailwindCSS
- shadcn/ui

**Backend**

- FastAPI
- Pydantic
- Playwright
- Notion API
- Jinja2
- Redis (caching & background jobs)

**Infrastructure**

- Docker
- uv
- Makefile

## Development

### Docker (recommended)

```bash
# Create the shared network once (if it does not exist)
docker network create dev-net

make up      # start web + api services
make down    # stop services
make logs    # tail service logs
```

Services are routed via Traefik:

| Service | URL |
|---------|-----|
| Web | http://cv.localhost |
| API | http://cv-api.localhost |

### Local development (without full Docker stack)

```bash
# Root setup
make setup

# Terminal 1 — API
make dev-api
# or: cd apps/api && uvicorn app.main:app --reload --port 8000

# Terminal 2 — Web
make dev-web
# or: cd apps/web && npm run dev

# Both together
make dev
```

**API setup**

```bash
cd apps/api
uv sync --extra dev          # or: pip install -e ".[dev]"
cp .env.example .env         # set NOTION_API_TOKEN, REDIS_URL
uvicorn app.main:app --reload --port 8000
```

**Web setup**

```bash
cd apps/web
npm install
cp .env.example .env         # set NEXT_PUBLIC_API_URL
npm run dev
```

**Run tests**

```bash
cd apps/api
pytest tests/ -v
```

**Regenerate template preview images**

```bash
make previews
# or: make previews TEMPLATE=minimal
```

## Project Structure

```text
notion-resume-pipeline/
├── apps/
│   ├── api/                        # FastAPI backend
│   │   ├── app/
│   │   │   ├── core/               # Cache, Redis, logging, deps
│   │   │   ├── exceptions/         # Domain errors
│   │   │   ├── routers/            # HTTP endpoints (notion, resumes, jobs)
│   │   │   ├── schemas/            # Pydantic models (ResumeData, jobs, etc.)
│   │   │   ├── services/           # Notion client, parser, mapper, PDF
│   │   │   ├── templates/resume/   # Jinja2 HTML/CSS templates
│   │   │   ├── workers/            # ARQ background job workers
│   │   │   └── main.py
│   │   ├── scripts/                # Preview image generation
│   │   └── tests/
│   └── web/                        # Next.js dashboard
│       ├── app/                    # App router pages & API proxy
│       ├── components/             # UI, dashboard, export controls
│       └── lib/                    # Types, Markdown export, storage
├── infra/docker/                   # Dockerfiles
├── docker-compose.yml
├── Makefile
└── package.json                    # Root dev tooling (concurrently)
```

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check (includes Redis status) |
| `POST` | `/api/v1/notion/import` | Import and normalize a Notion page → `ResumeData` JSON |
| `POST` | `/api/v1/notion/sync` | Force-refresh cached data from Notion |
| `GET` | `/api/v1/notion/preview/{page_id}` | Render resume HTML preview (`?template=&variant=`) |
| `GET` | `/api/v1/notion/pdf/{page_id}` | Export resume as PDF (`?template=&variant=`) |
| `GET` | `/api/v1/resumes/templates` | List available templates |
| `POST` | `/api/v1/jobs/export` | Enqueue async export job (PDF/Markdown/HTML) |
| `GET` | `/api/v1/jobs/{job_id}` | Poll export job status |

Interactive docs: http://localhost:8000/docs

### Export behaviour

| Format | Where it runs | Source |
|--------|---------------|--------|
| PDF | Backend (Playwright) | `/api/v1/notion/pdf/{page_id}` |
| JSON | Frontend | Normalized `ResumeData` from import |
| Markdown | Frontend | Converted from `ResumeData` in the browser |

## Notion Page Format

Structure your Notion resume with standard headings:

- `heading_1` — Name (fallback if page title property is empty)
- `heading_2` — Section headers (`Experience`, `Skills`, `Projects`, `Education`, `Summary`, …)
- `heading_3` — Job, project, or skill-category entries (`Role — Company`)
- Bullets — Highlights and achievements
- Paragraphs — Dates, descriptions, contact info

## Future Roadmap

- Additional templates
- AI-assisted resume tailoring
- Resume editing
- Template customization (colors, variants)
- Additional import sources (LinkedIn, JSON upload, etc.)

## License

MIT (or your chosen license)
