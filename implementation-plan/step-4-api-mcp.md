# Step 4 — REST API + MCP server

## Goal
Expose project/file management and search over REST for the UI, and the same search
capability as MCP tools over streamable HTTP at `/mcp`, all in one FastAPI app.

## Files
- `backend/app/api.py` — APIRouter with all `/api/*` routes
- `backend/app/mcp_server.py` — FastMCP instance + tools
- `backend/app/main.py` — mount router + MCP app + static
- `backend/tests/test_api.py` — TestClient tests (validation paths; no network)

## REST routes
| Method & path | Behavior |
|---|---|
| `GET /api/projects` | list projects (+file counts) |
| `POST /api/projects` `{name}` | create; 409 on duplicate name; slug validation |
| `DELETE /api/projects/{id}` | drop Qdrant collection, delete files on disk + rows |
| `GET /api/projects/{id}/files` | list files with status/chunk_count/error |
| `POST /api/projects/{id}/files` | multipart upload (multiple), validate extension via `SUPPORTED_EXTENSIONS`, save to `uploads/<project>/`, create row `pending`, BackgroundTasks → `ingest_file` |
| `DELETE /api/projects/{id}/files/{fid}` | `remove_file` (points + disk + row) |
| `GET /api/projects/{id}/search?q=` | 422 if len(q) > 512 or empty; runs `retrieval.search`, ≤3 files |
| `GET /api/mcp-info` | `{url, config_json}` for the UI popup |

Notes: ingestion runs in BackgroundTasks (single-process OK for v1); Docling/Qdrant
calls are sync — run via `run_in_threadpool` where handlers are async, or plain `def`
handlers (FastAPI thread pool) — use plain `def`.

## MCP tools (FastMCP, streamable HTTP)
- `list_projects() -> list[{name, files}]`
- `search_documents(query, project) -> {results: ≤3 files with locations & snippets}` — same length limit
- `get_chunk_context(project, chunk_id) -> {prev, chunk, next}` — via Qdrant `retrieve` on prev/next ids
Mounting: `mcp = FastMCP("doc-kb", stateless_http=True)`; in main.py mount
`app.mount("/mcp-server", mcp.streamable_http_app())` — actual client URL uses the app's
`/mcp` path; verify the exact mount pattern against the installed mcp SDK version, keep
final URL `http://host:8000/mcp`. Combined lifespan (init_db + mcp session manager).

## Edge cases
- Upload of unsupported extension → 400 with supported list
- Search on empty project → `{"results": []}`
- Duplicate file name in project → replace: delete old points/row first
- Project delete while a file is indexing → best effort (v1)

## Verification checklist
- [x] pytest: 10 passed (CRUD, duplicate 409, bad ext 400, query length/empty 422, empty-project search, mcp-info)
- [x] Live: sample.docx uploaded via API → pending → indexed; replace-by-name works
- [x] Live: search "meal reimbursement limit" → sample.docx #1 with "Employee Handbook > Expense Policy"
- [x] MCP client over streamable HTTP: tools = list_projects, search_documents, get_chunk_context; search returned xlsx (sheet Revenue) / pptx (slide 1) / md
- [x] `GET /api/mcp-info` returns `{url, config_json}` with mcpServers block
