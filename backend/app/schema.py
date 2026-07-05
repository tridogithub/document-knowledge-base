from dataclasses import dataclass, field, asdict


@dataclass
class Chunk:
    """One retrievable unit; mirrors the Qdrant payload schema."""

    id: str
    project_id: str
    file_id: str
    file_path: str
    file_name: str
    file_type: str
    text: str
    # text with heading context prepended, used for embedding only
    embed_text: str
    chunk_index: int
    # original location of the file on the user's machine, if known
    source_path: str | None = None
    section_path: list[str] = field(default_factory=list)
    page: int | None = None
    slide: int | None = None
    sheet: str | None = None
    row_range: list[int] | None = None
    line_start: int | None = None
    line_end: int | None = None
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None

    def payload(self) -> dict:
        d = asdict(self)
        d.pop("embed_text")
        return d
