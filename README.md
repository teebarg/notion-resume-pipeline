# Notion Resume Pipeline

A developer-focused resume generation platform that transforms structured Notion content into portable resume formats including Markdown, HTML, and PDF.

The project is designed as a document rendering pipeline rather than a traditional drag-and-drop resume builder.

## Features

- Import resume content directly from Notion
- Normalize Notion blocks into a structured resume schema
- Export resumes as:
  - Markdown
  - HTML
  - PDF
- Template-based rendering system
- Async PDF generation pipeline
- Shareable public resume links
- AI-assisted resume tailoring (planned)

---

## Architecture

```text
Notion API
    ↓
Resume Normalizer
    ↓
Canonical Resume JSON
    ↓
Render Engine
    ├── Markdown
    ├── HTML
    └── PDF (Puppeteer)