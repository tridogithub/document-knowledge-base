"""Ingestion pipeline: extract → chunk → embed → upsert, with status tracking."""

import sys
import traceback
from pathlib import Path

from sqlmodel import select

from . import embedding, sparse, vectorstore
from .config import settings
from .db import File, FileStatus, Project, get_session, init_db


def ingest_file(file_id: str) -> None:
    with get_session() as session:
        file = session.get(File, file_id)
        if file is None:
            return
        project = session.get(Project, file.project_id)
        file.status = FileStatus.indexing
        file.error = None
        session.add(file)
        session.commit()
        session.refresh(file)
        session.refresh(project)

    try:
        from .extractors import get_extractor

        extractor = get_extractor(file.file_type)
        chunks = extractor(
            file.file_path,
            project_id=project.id,
            file_id=file.id,
            file_name=file.file_name,
            file_type=file.file_type,
        )
        if not chunks:
            raise ValueError("No text content could be extracted from this file")

        dense = embedding.embed_texts([c.embed_text for c in chunks])

        with get_session() as session:
            p = session.get(Project, project.id)
            if p.vector_size is None:
                p.vector_size = len(dense[0])
                session.add(p)
                session.commit()
            vector_size = p.vector_size

        vectorstore.ensure_collection(project.id, vector_size)
        # idempotent re-ingest: clear any previous points for this file
        vectorstore.delete_file_points(project.id, file.id)

        sparse_vecs = sparse.encode([c.text for c in chunks])
        vectorstore.upsert_chunks(project.id, chunks, dense, sparse_vecs)

        with get_session() as session:
            f = session.get(File, file.id)
            f.status = FileStatus.indexed
            f.chunk_count = len(chunks)
            session.add(f)
            session.commit()
    except Exception as e:
        traceback.print_exc()
        with get_session() as session:
            f = session.get(File, file.id)
            f.status = FileStatus.failed
            f.error = str(e)[:1000]
            session.add(f)
            session.commit()


def remove_file(file_id: str) -> None:
    with get_session() as session:
        file = session.get(File, file_id)
        if file is None:
            return
        try:
            vectorstore.delete_file_points(file.project_id, file.id)
        except Exception:
            traceback.print_exc()
        Path(file.file_path).unlink(missing_ok=True)
        session.delete(file)
        session.commit()


def _cli() -> None:
    """Usage: python -m app.ingest <project_name> <file_path>"""
    init_db()
    project_name, file_path = sys.argv[1], Path(sys.argv[2])
    with get_session() as session:
        project = session.exec(select(Project).where(Project.name == project_name)).first()
        if project is None:
            project = Project(name=project_name, collection_name="")
            project.collection_name = vectorstore.collection_name(project.id)
            session.add(project)
            session.commit()
            session.refresh(project)
        dest = settings.uploads_dir / project.id / file_path.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(file_path.read_bytes())
        file = File(
            project_id=project.id,
            file_name=file_path.name,
            file_path=str(dest),
            file_type=file_path.suffix.lstrip(".").lower(),
        )
        session.add(file)
        session.commit()
        session.refresh(file)
    ingest_file(file.id)
    with get_session() as session:
        f = session.get(File, file.id)
        print(f"{f.file_name}: {f.status.value} chunks={f.chunk_count} error={f.error}")


if __name__ == "__main__":
    _cli()
