"""Markdown / plain-text extractor with heading-path and line-number tracking."""

import re
import uuid
from pathlib import Path

from ..schema import Chunk

MAX_CHARS = 2000  # ~500 tokens
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def _link(chunks: list[Chunk]) -> list[Chunk]:
    for i, c in enumerate(chunks):
        c.chunk_index = i
        c.prev_chunk_id = chunks[i - 1].id if i > 0 else None
        c.next_chunk_id = chunks[i + 1].id if i < len(chunks) - 1 else None
    return chunks


def extract_text_file(
    path: str | Path,
    *,
    project_id: str,
    file_id: str,
    file_name: str,
    file_type: str,
    source_path: str | None = None,
) -> list[Chunk]:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    is_md = file_type in {"md", "markdown"}

    chunks: list[Chunk] = []
    heading_stack: list[tuple[int, str]] = []  # (level, title)
    buf: list[str] = []
    buf_start = 1

    def flush(end_line: int) -> None:
        nonlocal buf, buf_start
        text = "\n".join(buf).strip()
        if text:
            section = [t for _, t in heading_stack]
            chunks.append(
                Chunk(
                    id=str(uuid.uuid4()),
                    project_id=project_id,
                    file_id=file_id,
                    file_path=file_name,
                    file_name=file_name,
                    file_type=file_type,
                    text=text,
                    embed_text=(" > ".join(section) + "\n" + text) if section else text,
                    chunk_index=0,
                    source_path=source_path,
                    section_path=section,
                    line_start=buf_start,
                    line_end=end_line,
                )
            )
        buf = []
        buf_start = end_line + 1

    for lineno, line in enumerate(lines, start=1):
        m = HEADING_RE.match(line) if is_md else None
        if m:
            flush(lineno - 1)
            level, title = len(m.group(1)), m.group(2).strip()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append((level, title))
            buf_start = lineno
            continue
        buf.append(line)
        if sum(len(l) + 1 for l in buf) >= MAX_CHARS and (not line.strip() or not is_md):
            flush(lineno)

    flush(len(lines))
    return _link(chunks)
