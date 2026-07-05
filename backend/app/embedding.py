from openai import OpenAI

from .config import settings

_client: OpenAI | None = None


def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            base_url=settings.embedding_base_url,
            api_key=settings.embedding_api_key,
        )
    return _client


def embed_texts(texts: list[str], *, is_query: bool = False) -> list[list[float]]:
    prefix = settings.embedding_query_prefix if is_query else settings.embedding_doc_prefix
    out: list[list[float]] = []
    for i in range(0, len(texts), settings.embedding_batch_size):
        batch = [prefix + t for t in texts[i : i + settings.embedding_batch_size]]
        resp = client().embeddings.create(model=settings.embedding_model, input=batch)
        out.extend(d.embedding for d in sorted(resp.data, key=lambda d: d.index))
    return out


def detect_dim() -> int:
    return len(embed_texts(["dimension probe"])[0])
