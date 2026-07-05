# Step 6 — Packaging & docs

## Goal
`git clone` → `cp .env.example .env` (fill embedding creds) → `docker compose up --build`
gives a fully working system: UI at :8000, MCP at :8000/mcp, Qdrant at :6333.

## Files
- `Dockerfile` (repo root) — multi-stage:
  1. `node:22-alpine` → `npm ci && npm run build` in frontend/
  2. `python:3.12-slim` → install uv, `uv sync --frozen --no-dev` in backend/,
     copy frontend dist → `app/static`, `CMD uvicorn app.main:app --host 0.0.0.0`
- `.dockerignore` — node_modules, .venv, data, dist, samples, .git
- `docker-compose.yml` — already exists from Step 1 (app + qdrant, volumes, healthcheck)
- `README.md` — quick start, architecture, env vars, MCP config, API table, dev setup

## Notes
- Docling pulls PyTorch → image is large (~4–6 GB) and first build slow; document this.
- Pre-download HF models (docling layout + fastembed bm25) at build time is optional;
  v1 downloads at first ingest (document HF_HOME volume note).
- `EMBEDDING_*` vars come from `.env` via compose `env_file`.

## Verification checklist
- [x] `docker compose build` succeeds (multi-stage: node UI build → python + uv)
- [x] `docker compose up -d` → qdrant healthy, app started, UI 200, /api/health ok
- [x] Dockerized e2e: uploaded sample.pptx + notes.txt → indexed (3 + 1 chunks); search "tiered discount annual contracts" → sample.pptx slide 2 "Pricing Strategy" #1
- [x] README covers quick start, .env, MCP config, API table, dev setup
