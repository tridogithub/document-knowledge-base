# Document Knowledge Base — Implementation Plan

## Context

Build a ready-to-run, dockerized RAG document knowledge base per [document-knowledge-base/features.md](/Users/dovantri/Documents/TriDV/AI-research/document-knowledge-base/features.md). Business documents (pptx, xlsx, docx, pdf, md, txt) are ingested with hierarchical chunking and rich location metadata, stored in a local vector DB, and retrieved via hybrid (keyword + semantic) search returning the **top-3 most relevant files** with exact locations. Consumers: an MCP server (for AI coding agents) and a small web UI (project management, file upload/removal, search, MCP config popup).

Tech decisions were researched and agreed in [document-knowledge-base/plan.md](/Users/dovantri/Documents/TriDV/AI-research/document-knowledge-base/plan.md):
- **Docling** for extraction (keeps page/slide/sheet/heading provenance) + plain heading/line-tracking readers for md/txt
- **Docling HybridChunker** for hierarchy-aware chunking (heading-path metadata)
- **Qdrant** (Docker) — one collection per project; hybrid = dense + FastEmbed BM25 sparse, RRF fusion
- **Embeddings** via OpenAI-compatible env config; dev endpoint: `https://mkp-api.fptcloud.com/v1` (FPT Cloud — model name set via env)
- **FastAPI** backend + **FastMCP** mounted at `/mcp` (streamable HTTP) + **React/Vite** UI served as static files
- **SQLite** registry for projects/files/ingest status
- User decisions: React+Vite UI; code lives in `document-knowledge-base/` (git init there); FPT Cloud endpoint for dev

## Repo layout (all under `document-knowledge-base/`)

```
docker-compose.yml          # app + qdrant
.env.example                # EMBEDDING_BASE_URL / EMBEDDING_API_KEY / EMBEDDING_MODEL / QDRANT_URL
backend/
  pyproject.toml            # uv-managed
  app/
    config.py               # pydantic-settings from env
    db.py                   # SQLite (sqlmodel or sqlite3): projects, files
    extractors/             # docling.py (pdf/docx/pptx/xlsx), text.py (md/txt w/ heading+line tracking)
    chunking.py             # HybridChunker → Chunk dataclass w/ payload schema
    embedding.py            # OpenAI-compatible client (batched), dim auto-detect
    sparse.py               # FastEmbed Qdrant/bm25 encoder
    vectorstore.py          # Qdrant: collection per project, upsert, delete by file_id, hybrid query
    retrieval.py            # hybrid RRF → per-file aggregation → top-3
    ingest.py               # pipeline: extract → chunk → embed → upsert; status updates
    api.py                  # FastAPI routes
    mcp_server.py           # FastMCP tools, mounted at /mcp
    main.py                 # app assembly, static file serving
  Dockerfile                # multi-stage: build frontend, install backend
frontend/                   # React + Vite + TypeScript
  src/pages: Projects, ProjectDetail (upload/files/search), McpModal
README.md
```

## Supported document types (explicit requirement)

Every format below gets a first-class extractor, location metadata, and a dedicated test fixture in verification:

| Format | Extractor | Location metadata stored per chunk |
|---|---|---|
| **PPTX** | Docling | slide number, slide title / heading path, speaker notes flagged |
| **PDF** | Docling (layout model; OCR fallback for scanned pages) | page number, section heading path |
| **Excel (XLSX/XLS)** | Docling (tables serialized per sheet) | sheet name, table index, best-effort row range |
| **DOCX** | Docling | heading path (H1>H2>H3), page (when derivable), paragraph index |
| **Markdown (MD)** | Native reader | heading path, line_start / line_end |
| **Plain text (TXT)** | Native reader | line_start / line_end |

Upload validation rejects other extensions with a clear error; the extractor registry is a dict keyed by extension so adding formats later (html, csv) is one entry.

## Chunk payload schema (Qdrant)

`project_id, file_id, file_path, file_name, file_type, section_path[], page, slide, sheet, row_range, line_start, line_end, chunk_index, prev_chunk_id, next_chunk_id, text`

## Working process (user requirement)

For **each step from Step 2 onward**, before writing code:
1. Write a detailed implementation plan to `document-knowledge-base/implementation-plan/step-N-<name>.md` covering: goal, files to create/modify, function signatures & data flow, library APIs used (verified against current docs), edge cases, and the step's own verification checklist.
2. Implement by following that document.
3. Run the step's verification checklist; record outcomes (checkboxes) back into the step document before moving on.

Directory: `document-knowledge-base/implementation-plan/` — expected files:
`step-2-ingestion.md`, `step-3-retrieval.md`, `step-4-api-mcp.md`, `step-5-frontend.md`, `step-6-packaging.md`.

## Implementation steps

### Step 1 — Scaffold
- `git init`, backend skeleton with uv + FastAPI hello, config from env (reuse the FPT `.env` values via `.env.example` naming), SQLite models `projects(id, name, collection_name, created_at)` and `files(id, project_id, file_name, file_path, status[pending|indexing|indexed|failed], chunk_count, error)`.
- docker-compose with qdrant service early so everything develops against it.

### Step 2 — Ingestion pipeline
- Extractor interface `extract(path) -> list[Section/Item with provenance]`; Docling converter for pdf/docx/pptx/xlsx; lightweight md/txt reader tracking heading path + line numbers.
- Chunking via Docling `HybridChunker` (max ~512 tokens), map provenance → payload schema; assign UUIDs and prev/next links.
- Embedding client: OpenAI-compatible `/embeddings`, batch of ~64, auto-detect vector dim on first call (store per project).
- Sparse: FastEmbed `Qdrant/bm25`.
- Qdrant: create collection (named vectors `dense` + sparse `bm25`), payload index on `file_id`; upsert; `delete_by_file(file_id)`.
- Verify with a CLI entry (`python -m app.ingest`) against 2–3 real sample docs.

### Step 3 — Retrieval
- Hybrid query: Query API prefetch dense top-20 + sparse top-20 → RRF → ~30 chunks.
- Aggregate per file: score = max chunk score + 0.05·log(1+extra hits); return top-3 files each with up to 3 best chunk locations + snippets.

### Step 4 — REST API + MCP
- Routes: `GET/POST/DELETE /api/projects`, `POST /api/projects/{id}/files` (multipart → save to data volume → BackgroundTasks ingest), `GET /api/projects/{id}/files`, `DELETE /api/projects/{id}/files/{fid}`, `GET /api/projects/{id}/search?q=` (max 512 chars, 422 otherwise), `GET /api/mcp-info`.
- FastMCP tools: `search_documents(query, project_name) -> top-3 files w/ locations`, `list_projects()`, `get_chunk_context(chunk_id)` (uses prev/next). Mount streamable-HTTP app at `/mcp` in main FastAPI app.

### Step 5 — Frontend (React + Vite + TS)
- Projects page: list/create/delete.
- Project detail: drag-drop upload, file table with status polling (2s while any file `pending|indexing`), remove button.
- Search bar (maxLength enforced) → result cards: file name/path, file type icon, locations (page/slide/sheet/section path), snippet, score.
- "MCP Server" button → modal showing `{"mcpServers":{"doc-kb":{"type":"http","url":"http://localhost:8000/mcp"}}}` with copy button (URL from `/api/mcp-info`).
- Vite dev proxy to backend; production build copied into image, served by FastAPI.

### Step 6 — Packaging & docs
- Multi-stage Dockerfile (node build → python:3.12-slim + uv sync; note: Docling image is large, first build slow).
- docker-compose: `qdrant` (volume `qdrant_data`), `app` (volume `app_data` for SQLite + uploaded files), healthchecks, `env_file: .env`.
- README: setup, `.env`, `docker compose up`, MCP config snippet, API summary.

## Verification

1. `docker compose up` from a clean clone + `.env` → UI reachable at `http://localhost:8000`, Qdrant dashboard at `:6333/dashboard`.
2. Create a project, upload one file of **each supported type — pptx, pdf, xlsx, docx, md, txt** → all reach `indexed` with chunk_count > 0; spot-check payloads in Qdrant dashboard: pptx chunks carry slide numbers, pdf chunks page numbers, xlsx chunks sheet names, docx chunks heading paths, md/txt chunks line ranges.
3. UI search with a query known to hit a specific slide/page → correct file ranked in top-3 with correct location shown.
4. Remove a file → its points gone from Qdrant (count drops), search no longer returns it.
5. MCP end-to-end: add the JSON config to Claude Code, call `search_documents` — verify ≤3 files returned with locations.
6. Backend unit tests (pytest): chunk payload mapping for each extractor, file-aggregation ranking logic, query length validation.

## Notes / risks

- Embedding model name for FPT Cloud must be set in `.env` (`EMBEDDING_MODEL`); dim auto-detection handles unknown sizes.
- Docling's XLSX provenance is sheet-level (plus table structure) — row_range is best-effort.
- Large PPTX/PDF ingestion can take minutes on CPU; status polling in UI covers UX.
