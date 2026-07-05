# Step 5 — Web UI (React + Vite + TypeScript)

## Goal
Single-page UI covering: project management, per-project file add/remove with ingest
status, search bar (length-limited) showing top-3 results with locations, and an
"MCP Server" popup with copyable config JSON.

## Files
- `frontend/` — Vite React-TS app (`npm create vite@latest`)
- `src/api.ts` — typed fetch helpers for all `/api/*` endpoints
- `src/App.tsx` — layout: sidebar (project list + create/delete) & main panel
- `src/components/ProjectPanel.tsx` — upload (file input + drag-drop), file table with
  status badges (polling every 2s while any file pending/indexing), delete buttons
- `src/components/SearchBar.tsx` — input (maxLength from `/api` limit = 512), results
  as cards: file name, type badge, score, per-match location line + snippet
- `src/components/McpModal.tsx` — fetches `/api/mcp-info`, shows URL + JSON, copy button
- `src/styles.css` — small hand-rolled stylesheet (no UI framework, keep it light)
- `vite.config.ts` — dev proxy `/api` + `/mcp` → `localhost:8000`; `build.outDir` left
  default `dist` (copied to `backend/app/static` at Docker build; a `predev`-free flow)

## Behaviors
- Project create: prompt-style inline form; errors (409/422) shown inline
- Upload: multiple files; unsupported extension → alert with server message
- Status polling only while needed; badge colors: pending grey, indexing blue,
  indexed green, failed red (tooltip = error)
- Search: Enter or button; renders ≤3 result cards; empty → "No matching documents"
- MCP modal: `navigator.clipboard.writeText`, "Copied!" feedback

## Verification checklist
- [x] `npm run build` clean (197 kB JS, 3 kB CSS)
- [x] Built dist served by FastAPI at / (HTTP 200, assets load); /api/mcp-info feeding the modal verified
- [x] All UI operations backed by API endpoints verified live in Step 4 (upload→indexed, search with locations, delete)
- [ ] Manual browser click-through (open http://localhost:8000) — for the user to eyeball
