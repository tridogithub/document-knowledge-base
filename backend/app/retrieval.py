"""Hybrid (dense + BM25) retrieval with RRF fusion and per-file aggregation."""

import math

from qdrant_client import models

from . import embedding, sparse, vectorstore
from .config import settings

PREFETCH_K = 20
CHUNK_LIMIT = 30
SNIPPET_CHARS = 300
MATCHES_PER_FILE = 3


def _location(payload: dict) -> dict:
    loc = {}
    for key in ("page", "slide", "sheet", "row_range", "line_start", "line_end"):
        if payload.get(key) is not None:
            loc[key] = payload[key]
    if payload.get("section_path"):
        loc["section"] = " > ".join(payload["section_path"])
    return loc


def aggregate_by_file(points: list[dict], top_k: int) -> list[dict]:
    """points: [{score, payload}] → top_k files ranked by max score + multi-hit bonus."""
    files: dict[str, dict] = {}
    for pt in points:
        pl = pt["payload"]
        entry = files.setdefault(
            pl["file_id"],
            {
                "file_id": pl["file_id"],
                "file_name": pl["file_name"],
                "file_path": pl["file_path"],
                "source_path": pl.get("source_path") or pl["file_name"],
                "file_type": pl["file_type"],
                "matches": [],
            },
        )
        entry["matches"].append(
            {
                "chunk_id": pl["id"],
                "score": pt["score"],
                "location": _location(pl),
                "snippet": pl["text"][:SNIPPET_CHARS],
            }
        )
    for f in files.values():
        f["matches"].sort(key=lambda m: m["score"], reverse=True)
        f["score"] = round(
            f["matches"][0]["score"] + 0.05 * math.log1p(len(f["matches"]) - 1), 6
        )
        f["matches"] = f["matches"][:MATCHES_PER_FILE]
    return sorted(files.values(), key=lambda f: (-f["score"], f["file_name"]))[:top_k]


def search(project_id: str, query: str) -> list[dict]:
    name = vectorstore.collection_name(project_id)
    if not vectorstore.client().collection_exists(name):
        return []

    dense_q = embedding.embed_texts([query], is_query=True)[0]
    sparse_q = sparse.encode_query(query)

    res = vectorstore.client().query_points(
        collection_name=name,
        prefetch=[
            models.Prefetch(query=dense_q, using=vectorstore.DENSE, limit=PREFETCH_K),
            models.Prefetch(query=sparse_q, using=vectorstore.SPARSE, limit=PREFETCH_K),
        ],
        query=models.FusionQuery(fusion=models.Fusion.RRF),
        limit=CHUNK_LIMIT,
        with_payload=True,
    )
    points = [{"score": p.score, "payload": p.payload} for p in res.points]
    return aggregate_by_file(points, settings.top_k_files)
