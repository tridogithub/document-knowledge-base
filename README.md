# Document Knowledge Base

A local, dockerized RAG knowledge base for business documents. Upload **pptx, pdf,
xlsx, docx, md, txt** files; they are parsed with location metadata (page / slide /
sheet / section / line numbers), hierarchically chunked, and indexed into Qdrant with
**hybrid search** (BM25 keyword + semantic embeddings, RRF fusion). Search returns the
**top-3 most relevant files** with exact locations — via a web UI or an **MCP server**
your AI coding agent can call.

```
Browser ──► Web UI (React) ─┐
AI agent ─► MCP  /mcp ──────┼─► FastAPI app ──► Qdrant (dense + BM25 sparse)
                            │      │
                            │      └─► SQLite registry + uploaded files
                            └─► REST /api/*
```

## Quick start (Docker)

Requirements: Docker with compose.

```bash
cp .env.example .env    # fill in your embedding endpoint (OpenAI-compatible)
docker compose up --build
```

- Web UI: http://localhost:8000
- MCP endpoint: http://localhost:8000/mcp (streamable HTTP)
- Qdrant dashboard: http://localhost:6333/dashboard

> First build is slow and the image is large (Docling ships ML models via PyTorch).
> The layout/OCR models download on first ingest into the `app_data` volume.

## Configuration (.env)

| Variable | Description | Example |
|---|---|---|
| `EMBEDDING_BASE_URL` | OpenAI-compatible endpoint | `https://api.openai.com/v1` |
| `EMBEDDING_API_KEY` | API key | `sk-...` |
| `EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |
| `EMBEDDING_QUERY_PREFIX` | Optional (e5 models: `query: `) | empty |
| `EMBEDDING_DOC_PREFIX` | Optional (e5 models: `passage: `) | empty |
| `PUBLIC_BASE_URL` | URL shown in the MCP popup | `http://localhost:8000` |

Any OpenAI-compatible server works: OpenAI, Azure, vLLM, Ollama, FPT Cloud
(`multilingual-e5-large` with the e5 prefixes), etc. The vector dimension is
auto-detected per project.

## Using the MCP server

Click **MCP Server** in the UI and copy the config, or add manually:

```json
{ "mcpServers": { "doc-kb": { "type": "http", "url": "http://localhost:8000/mcp" } } }
```

Tools exposed:
- `list_projects()` — projects and file counts
- `search_documents(query, project)` — up to 3 relevant files with locations + snippets
- `get_chunk_context(project, chunk_id)` — a chunk with its previous/next neighbors

## REST API

| Method & path | Purpose |
|---|---|
| `GET/POST /api/projects`, `DELETE /api/projects/{id}` | manage projects |
| `GET/POST /api/projects/{id}/files`, `DELETE .../files/{fid}` | upload (multipart, background indexing) / remove files |
| `GET /api/projects/{id}/search?q=` | hybrid search, max 512-char query, ≤3 files |
| `GET /api/mcp-info` | MCP endpoint + copy-paste config |

## Development

```bash
# Qdrant
docker compose up qdrant -d

# Backend (http://localhost:8000)
cd backend && cp ../.env.example .env  # edit
uv sync && uv run uvicorn app.main:app --reload

# Frontend dev server with proxy (http://localhost:5173)
cd frontend && npm install && npm run dev

# Tests
cd backend && uv run pytest

# CLI ingestion
cd backend && uv run python -m app.ingest <project-name> <file>
```

## How retrieval works

1. Documents are parsed by **Docling** (pdf/docx/pptx/xlsx) or native readers (md/txt),
   keeping provenance: page, slide, sheet name, heading path, line range.
2. **Hierarchical chunking** (Docling HybridChunker, ~512 tokens) embeds each chunk with
   its heading context; chunks keep prev/next links for neighborhood lookup.
3. Each chunk gets a dense vector (your embedding endpoint) and a **BM25 sparse vector**
   (FastEmbed, local CPU).
4. A query runs both searches in Qdrant, fuses them with **Reciprocal Rank Fusion**,
   then results are aggregated per file (best chunk score + multi-hit bonus) →
   **top-3 files** with their best-matching locations.
