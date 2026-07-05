# Step 3 — Hybrid retrieval + file aggregation

## Goal
`search(project_id, query)` → up to **3 files**, each with score, best chunk locations
(page/slide/sheet/section/lines) and snippets, using hybrid dense+BM25 search with RRF fusion.

## Files
- `backend/app/retrieval.py` — new
- `backend/tests/test_retrieval.py` — aggregation unit tests

## Design
1. Dense query vector: `embedding.embed_texts([query], is_query=True)` (e5 `query: ` prefix).
2. Sparse query vector: `sparse.encode_query(query)` (BM25, no IDF weighting client-side — collection has `Modifier.IDF`).
3. Qdrant Query API on `kb_<project_id>`:
   - `prefetch=[dense top-20 ("dense"), sparse top-20 ("bm25")]`
   - `query=FusionQuery(fusion=RRF)`, `limit=30`, `with_payload=True`
4. Aggregate per `file_id`:
   - `file_score = max(chunk_scores) + 0.05 * log1p(len(chunks) - 1)`
   - sort desc, take top `settings.top_k_files` (3)
   - per file keep up to 3 best chunks → `location` dict (only non-null of page/slide/sheet/row_range/line_start/line_end + section_path) + snippet (first 300 chars)
5. Return shape:
```python
{"query": ..., "results": [
  {"file_id","file_name","file_path","file_type","score",
   "matches":[{"chunk_id","score","location":{...},"snippet"}]}]}
```
Empty/missing collection → empty results (not an error).

## Edge cases
- Project with no indexed files → `[]`
- Query returning < 3 files → return what exists
- Identical scores → stable ordering by file_name for determinism in tests

## Verification checklist
- [x] Unit tests (3) pass: strong-chunk ranking, multi-hit tie-break bonus, top-k + match shape
- [x] Live: "revenue growth in APAC region" → sample.xlsx (sheet "Revenue") #1, sample.pptx (slide 1) #2
- [x] Live: "best sushi neighborhood in Tokyo" → tokyo.md with lines 51–63 + section heading
- [x] Live: "remote work policy days per week" → sample.docx ("Employee Handbook > Remote Work Policy") #1; ≤3 files returned
