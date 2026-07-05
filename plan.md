# Document Knowledge Base — Research & Implementation Plan

Goal: a ready-to-run, dockerized RAG knowledge base over business documents
(pptx, xlsx, docx, pdf, md, txt) that returns the **top-3 most relevant files**
(with exact locations: page / slide / sheet / section) via hybrid search,
exposed both through an MCP server and a small web UI with per-project isolation.

---

## 1. Technology research & recommendations

### 1.1 Document extraction — **Docling** (IBM, open source)

| Option | Verdict |
|---|---|
| **Docling** | ✅ Recommended. Parses PDF, DOCX, PPTX, XLSX, MD, HTML natively. Crucially, it keeps **provenance**: page numbers, headings hierarchy, slide index, table cells — exactly the metadata this system needs. ~88% F1 on benchmarks, fast, fully local. |
| MarkItDown (Microsoft) | Very light, but flattens everything to plain Markdown — you lose page/slide/section location info. Good fallback for `.txt`/`.md` only. |
| Unstructured | Broad format support but heavier dependency tree and weaker table extraction than Docling. |
| LlamaParse | Best accuracy but cloud API + $/page — conflicts with the "run locally in one shot" requirement. |

Decision: **Docling** for pdf/docx/pptx/xlsx; plain readers for md/txt (they need no ML parsing, just line/heading tracking).

### 1.2 Chunking — **hierarchical, Docling `HybridChunker`**

- Docling's `HybridChunker` is hierarchy-aware: each chunk carries its **heading path** (e.g. `Chapter 2 > Pricing > Discounts`), page/slide provenance, and is token-budgeted for the embedding model. This satisfies the "hierarchical chunking" requirement without pulling in the whole LlamaIndex framework.
- Because the goal is *finding files*, not answer generation, we retrieve at **chunk level and aggregate scores per file** (max + count-weighted), then return the top-3 files with their best-matching chunk locations. This is simpler and more robust than LlamaIndex `HierarchicalNodeParser` + `AutoMergingRetriever`, which is designed for feeding merged context to an LLM.
- For md/txt: heading-based splitter (level 1/2/3 headings → section path metadata, line numbers tracked).

### 1.3 Vector DB — **Qdrant** (docker, local)

| Option | Verdict |
|---|---|
| **Qdrant** | ✅ Recommended. Single small Docker container, runs fine on a laptop. **Native hybrid search**: dense vectors + sparse BM25 vectors fused with RRF in one Query API call. One **collection per project** gives the required project isolation. Has a built-in web dashboard for debugging. |
| LanceDB | Great embedded alternative (no extra container, Tantivy FTS + hybrid). Choose it if you ever want a single-process build; Qdrant chosen because hybrid + multi-tenant story is more mature. |
| Chroma | Simplest API but weaker hybrid/keyword search; SQLite-backed, less suited past ~200k vectors. |
| Milvus Lite | Aimed at large-scale deployments; overkill here. |

Hybrid retrieval design (lightweight, no reranker model needed):
1. Dense query vector from the OpenAI-compatible embedding endpoint.
2. Sparse BM25 vector generated locally with **FastEmbed** (`Qdrant/bm25`, pure CPU, tiny).
3. Qdrant Query API prefetch (dense top-20 + sparse top-20) → **RRF fusion** → aggregate per file → **top-3 files**.

### 1.4 Embeddings — env-configured OpenAI-compatible

Only three env vars, works with OpenAI, Azure, Ollama, LM Studio, vLLM, etc.:

```
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=sk-...
EMBEDDING_MODEL=text-embedding-3-small
```

Vector size is auto-detected on first call and stored per project.

### 1.5 MCP server — **FastMCP** (official Python SDK)

- One `@mcp.tool` `search_documents(query, project)` returning ≤3 files with
  file path, locations (page/slide/sheet/section/lines), scores, and matched snippets.
  Optionally `list_projects` and `get_file_outline` tools.
- Transport: **streamable HTTP** mounted into the same FastAPI app
  (`/mcp` endpoint) — so one container serves UI + API + MCP, and the UI's
  "MCP Server" button can show a copy-paste JSON like:

```json
{ "mcpServers": { "doc-kb": { "type": "http", "url": "http://localhost:8000/mcp" } } }
```

### 1.6 Backend & UI

- **FastAPI** backend (ingestion, search, project CRUD) + serves the built UI as static files.
- UI: small **React + Vite** SPA (or plain HTML+htmx if you want zero node tooling). Pages: project list → project detail (file upload/remove, ingest status) → search bar (query length-limited, shows top-3 results with locations) → "MCP Server" popup with copyable JSON.
- Job model: file upload triggers background ingestion (FastAPI `BackgroundTasks` is enough at this scale); a small SQLite table tracks projects/files/chunk counts so file removal can delete its points from Qdrant by filter (`file_id`).

### 1.7 Packaging

`docker-compose.yml` with two services: `qdrant` (official image, volume-mounted) and `app` (Python image with Docling + FastAPI + built UI). `.env.example` for the embedding settings. `docker compose up` = everything running.

---

## 2. Architecture

```
                       ┌─────────────────────────────────────────┐
 browser ── UI (React)─►  FastAPI app (one container)            │
                       │   /api/projects  /api/files  /api/search│
 AI agent ── MCP ──────►  /mcp  (FastMCP, streamable HTTP)       │
                       │                                         │
                       │  Ingestion: Docling → HybridChunker     │
                       │   → embed (OpenAI-compat) + BM25 sparse │
                       │  Retrieval: hybrid RRF → file aggregate │
                       │  SQLite: projects / files registry      │
                       └───────────────┬─────────────────────────┘
                                       │ gRPC/HTTP
                               ┌───────▼────────┐
                               │ Qdrant (docker)│  1 collection / project
                               │ dense + sparse │  payload = metadata
                               └────────────────┘
```

**Chunk payload schema** (stored in Qdrant):

```json
{
  "project_id": "...", "file_id": "...",
  "file_path": "reports/q3.pptx", "file_name": "q3.pptx", "file_type": "pptx",
  "section_path": ["Q3 Results", "Revenue"],
  "page": 12, "slide": 12, "sheet": "Summary", "row_range": [3, 40],
  "line_start": 120, "line_end": 148,
  "chunk_index": 37, "prev_chunk_id": "...", "next_chunk_id": "...",
  "text": "chunk text ..."
}
```

`prev/next_chunk_id` lets the AI (or a follow-up tool) fetch surrounding context.

---

## 3. Step-by-step implementation plan

### Phase 0 — Scaffold (½ day)
- Repo layout: `backend/` (FastAPI app, `pyproject.toml`, uv), `frontend/`, `docker-compose.yml`, `.env.example`, `README.md`.
- Config module reading `EMBEDDING_*` and `QDRANT_URL` env vars.
- SQLite models: `projects`, `files` (status: pending/indexed/failed, chunk_count).

### Phase 1 — Ingestion pipeline (2–3 days)
1. Extractor interface + implementations: Docling for pdf/docx/pptx/xlsx; markdown/txt readers with heading + line tracking.
2. Chunker: Docling `HybridChunker` (token limit sized to embedding model, e.g. 512), mapping each chunk to the payload schema above.
3. Embedding client (OpenAI-compatible, batched) + FastEmbed BM25 sparse encoder.
4. Qdrant writer: create collection per project (named vectors: `dense` + `sparse`), upsert points, payload index on `file_id`.
5. Delete path: remove all points by `file_id` filter when a file is removed.
6. CLI smoke test: `python -m app.ingest <project> <file>` then verify counts in Qdrant dashboard.

### Phase 2 — Retrieval (1–2 days)
1. Hybrid query: dense + sparse prefetch (top-20 each) → RRF fusion → top ~30 chunks.
2. File-level aggregation: group by `file_id`, score = max chunk score + small bonus per extra matching chunk; return **top-3 files**, each with its best chunks' locations and snippets.
3. Quality check with 10–15 real queries against your actual documents; tune prefetch sizes / chunk size.

### Phase 3 — API + MCP server (1–2 days)
1. REST: `POST/GET/DELETE /api/projects`, `POST /api/projects/{id}/files` (multipart, background ingest), `DELETE .../files/{id}`, `GET /api/projects/{id}/search?q=` (enforce query length limit, e.g. 512 chars).
2. FastMCP mounted at `/mcp`: `search_documents(query, project)`, `list_projects()`, optional `get_chunk_context(chunk_id)` using prev/next links.
3. Test MCP end-to-end from Claude Code / another agent via the JSON config.

### Phase 4 — Web UI (2–3 days)
1. Project list page (create/delete project).
2. Project page: drag-and-drop upload, file table with status + remove button (polling for ingest status).
3. Search bar with length limit → renders top-3 results: file name, path, location (page/slide/sheet/section), snippet.
4. "MCP Server" button → modal with server URL + ready-to-copy JSON config (copy button).

### Phase 5 — Packaging & docs (1 day)
1. Multi-stage Dockerfile (build frontend → copy into Python image), `docker-compose.yml` (app + qdrant + volumes), healthchecks.
2. `README.md`: prerequisites, `.env` setup, `docker compose up`, MCP config snippet, screenshots.
3. Sample docs + a `make demo` / script that ingests them for a one-shot demo.

### Phase 6 — Hardening (optional, ongoing)
- Concurrent-ingest queue (swap BackgroundTasks for a worker) if bulk uploads get big.
- Optional local cross-encoder reranker if top-3 precision needs a boost.
- Auth on the API/MCP endpoint if deployed beyond localhost.

**Total estimate: ~7–11 working days** for a solid v1.
