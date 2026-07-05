from qdrant_client import QdrantClient, models

from .config import settings
from .schema import Chunk

_client: QdrantClient | None = None

DENSE = "dense"
SPARSE = "bm25"


def client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url)
    return _client


def collection_name(project_id: str) -> str:
    return f"kb_{project_id}"


def ensure_collection(project_id: str, vector_size: int) -> None:
    name = collection_name(project_id)
    if client().collection_exists(name):
        return
    client().create_collection(
        collection_name=name,
        vectors_config={
            DENSE: models.VectorParams(size=vector_size, distance=models.Distance.COSINE)
        },
        sparse_vectors_config={
            SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)
        },
    )
    client().create_payload_index(
        collection_name=name,
        field_name="file_id",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )


def delete_collection(project_id: str) -> None:
    client().delete_collection(collection_name(project_id))


def delete_file_points(project_id: str, file_id: str) -> None:
    client().delete(
        collection_name=collection_name(project_id),
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[models.FieldCondition(key="file_id", match=models.MatchValue(value=file_id))]
            )
        ),
        wait=True,
    )


def upsert_chunks(
    project_id: str,
    chunks: list[Chunk],
    dense: list[list[float]],
    sparse: list[models.SparseVector],
    batch_size: int = 128,
) -> None:
    name = collection_name(project_id)
    points = [
        models.PointStruct(
            id=c.id,
            vector={DENSE: d, SPARSE: s},
            payload=c.payload(),
        )
        for c, d, s in zip(chunks, dense, sparse)
    ]
    for i in range(0, len(points), batch_size):
        client().upsert(collection_name=name, points=points[i : i + batch_size], wait=True)
