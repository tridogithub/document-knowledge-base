# Step 2 — Ingestion pipeline

## Goal
Given `(project, file on disk)` produce chunk points in the project's Qdrant collection, each carrying dense + BM25 sparse vectors and full location metadata (page/slide/sheet/section/lines), so retrieval can point the AI at exact file locations.

## Files
- `backend/app/schema.py` — `Chunk` dataclass = payload schema
- `backend/app/extractors/__init__.py` — registry `get_extractor(ext)`
- `backend/app/extractors/docling_extractor.py` — pdf/docx/pptx/xlsx via Docling `DocumentConverter` + `HybridChunker`
- `backend/app/extractors/text_extractor.py` — md/txt native reader (heading path + line ranges)
- `backend/app/embedding.py` — OpenAI-compatible client, batched, dim auto-detect
- `backend/app/sparse.py` — FastEmbed `Qdrant/bm25` sparse encoder
- `backend/app/vectorstore.py` — Qdrant collection mgmt, upsert, delete-by-file
- `backend/app/ingest.py` — pipeline orchestration + CLI (`python -m app.ingest <project> <file>`)

## Data flow
```
file → extractor → list[Chunk(text, metadata)]          (chunking inside extractor)
     → embedding.embed_batch(texts) → dense[·]
     → sparse.encode(texts) → SparseVector[·]
     → vectorstore.upsert(collection, chunks, dense, sparse)
     → update files.status / chunk_count in SQLite
```

## Design decisions
- **Docling path**: `DocumentConverter.convert(path)` → `DoclingDocument`; chunk with
  `docling.chunking.HybridChunker(tokenizer=..., max_tokens≈512, merge_peers=True)`.
  Per chunk read `chunk.meta.headings` → `section_path`, and provenance from
  `chunk.meta.doc_items[*].prov[*].page_no` → `page` (pdf/docx) or `slide` (pptx).
  XLSX: Docling emits one page per sheet; map `page_no` → sheet index, resolve sheet
  name via openpyxl sheet order. `contextualize()` text (headings prepended) is used
  for embedding; raw text stored in payload.
- **md/txt path**: split on headings (md) or blank-line paragraphs (txt), accumulate
  to ≈512-token chunks (approx 4 chars/token), track `line_start/line_end` and
  heading stack for `section_path`.
- **IDs**: chunk id = uuid4 hex; `prev_chunk_id`/`next_chunk_id` linked after chunk list built.
- **Qdrant collection** (`kb_<project_id>`): named dense vector `dense` (cosine, size
  auto-detected on first embedding call, persisted in `projects.vector_size`) + sparse
  vector `bm25` (modifier=IDF). Payload keyword index on `file_id`.
- **Idempotent re-ingest**: delete existing points for `file_id` before upsert.
- **Failure handling**: any exception → status `failed`, error message stored; partial
  points cleaned up by the same delete-by-file filter.

## Edge cases
- Empty/unparseable file → failed status with clear error, 0 chunks.
- Very large files: embed in batches of 64; upsert in batches of 128.
- Scanned PDFs: Docling OCR enabled by default pipeline (slow but correct).
- Chunk longer than embedding context: HybridChunker enforces max_tokens; text reader clamps.

## Verification checklist
- [x] `python -m app.ingest demo <sample.md>` → 25 chunks with line ranges + section paths (tokyo.md)
- [x] pptx → slide numbers; pdf → page numbers; xlsx → sheet names ("Revenue"/"Headcount"); docx → heading paths; txt → line ranges (verified via Qdrant scroll, 33 points)
- [x] Re-ingest is idempotent: `ingest_file` deletes points by `file_id` before upsert
- [x] Delete-by-file implemented (`remove_file`) — exercised again in Step 4 API tests
- [x] FPT Cloud endpoint verified: `multilingual-e5-large`, dim 1024 auto-detected and stored in `projects.vector_size`
