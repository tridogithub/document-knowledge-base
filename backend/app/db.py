import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Field, Session, SQLModel, create_engine

from .config import settings


def _uuid() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FileStatus(str, Enum):
    pending = "pending"
    indexing = "indexing"
    indexed = "indexed"
    failed = "failed"


class Project(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    name: str = Field(index=True, unique=True)
    collection_name: str
    vector_size: int | None = None
    created_at: datetime = Field(default_factory=_now)


class File(SQLModel, table=True):
    id: str = Field(default_factory=_uuid, primary_key=True)
    project_id: str = Field(index=True, foreign_key="project.id")
    file_name: str
    file_path: str  # path on disk under uploads_dir
    source_path: str | None = None  # original location on the user's machine, if known
    file_type: str  # extension without dot
    status: FileStatus = FileStatus.pending
    chunk_count: int = 0
    error: str | None = None
    created_at: datetime = Field(default_factory=_now)


engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args={"check_same_thread": False},
)


def _migrate() -> None:
    """Add columns introduced after the initial release to an existing sqlite file."""
    with engine.connect() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(file)")}
        if "source_path" not in cols:
            conn.exec_driver_sql("ALTER TABLE file ADD COLUMN source_path TEXT")
            conn.commit()


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _migrate()


def get_session() -> Session:
    return Session(engine)
