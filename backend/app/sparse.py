from fastembed import SparseTextEmbedding
from qdrant_client import models

_model: SparseTextEmbedding | None = None


def model() -> SparseTextEmbedding:
    global _model
    if _model is None:
        _model = SparseTextEmbedding(model_name="Qdrant/bm25")
    return _model


def encode(texts: list[str]) -> list[models.SparseVector]:
    return [
        models.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
        for e in model().embed(texts)
    ]


def encode_query(text: str) -> models.SparseVector:
    e = next(model().query_embed(text))
    return models.SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
