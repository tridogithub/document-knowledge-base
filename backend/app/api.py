import json
import mimetypes
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import func, select

from . import retrieval, vectorstore
from .config import settings
from .db import File, FileStatus, Project, get_session
from .extractors import SUPPORTED_EXTENSIONS
from .ingest import ingest_file, remove_file

router = APIRouter(prefix="/api")

NAME_RE = re.compile(r"^[\w][\w .-]{0,63}$")


def _get_project(session, project_id: str) -> Project:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/projects")
def list_projects() -> list[dict]:
    with get_session() as session:
        projects = session.exec(select(Project).order_by(Project.created_at)).all()
        counts = dict(
            session.exec(select(File.project_id, func.count()).group_by(File.project_id)).all()
        )
        return [
            {
                "id": p.id,
                "name": p.name,
                "created_at": p.created_at.isoformat(),
                "file_count": counts.get(p.id, 0),
            }
            for p in projects
        ]


@router.post("/projects", status_code=201)
def create_project(body: dict) -> dict:
    name = (body.get("name") or "").strip()
    if not NAME_RE.match(name):
        raise HTTPException(422, "Invalid project name (1-64 chars: letters, digits, . _ - space)")
    with get_session() as session:
        if session.exec(select(Project).where(Project.name == name)).first():
            raise HTTPException(409, f"Project '{name}' already exists")
        project = Project(name=name, collection_name="")
        project.collection_name = vectorstore.collection_name(project.id)
        session.add(project)
        session.commit()
        return {"id": project.id, "name": project.name}


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(project_id: str) -> None:
    with get_session() as session:
        project = _get_project(session, project_id)
        files = session.exec(select(File).where(File.project_id == project_id)).all()
        for f in files:
            remove_file(f.id)
        try:
            vectorstore.delete_collection(project_id)
        except Exception:
            pass
        session.delete(project)
        session.commit()


@router.get("/projects/{project_id}/files")
def list_files(project_id: str) -> list[dict]:
    with get_session() as session:
        _get_project(session, project_id)
        files = session.exec(
            select(File).where(File.project_id == project_id).order_by(File.created_at)
        ).all()
        return [
            {
                "id": f.id,
                "file_name": f.file_name,
                "source_path": f.source_path or f.file_name,
                "file_type": f.file_type,
                "status": f.status.value,
                "chunk_count": f.chunk_count,
                "error": f.error,
                "created_at": f.created_at.isoformat(),
            }
            for f in files
        ]


@router.post("/projects/{project_id}/files", status_code=202)
def upload_files(
    project_id: str,
    files: list[UploadFile],
    background: BackgroundTasks,
    source_dir: str | None = Form(None),
) -> list[dict]:
    # Browsers never expose a picked file's absolute path (security sandboxing),
    # so the true original location has to come from the user, e.g. the folder
    # they dragged the files from. This is purely descriptive metadata for
    # humans/agents to navigate back to the source — it is not read from disk.
    source_dir = (source_dir or "").strip().rstrip("/\\") or None

    out = []
    with get_session() as session:
        _get_project(session, project_id)
        for upload in files:
            ext = (upload.filename or "").rsplit(".", 1)[-1].lower()
            if ext not in SUPPORTED_EXTENSIONS or "." not in (upload.filename or ""):
                raise HTTPException(
                    400,
                    f"Unsupported file type for '{upload.filename}'. "
                    f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
                )
        for upload in files:
            ext = upload.filename.rsplit(".", 1)[-1].lower()
            # replace an existing file with the same name
            existing = session.exec(
                select(File).where(
                    File.project_id == project_id, File.file_name == upload.filename
                )
            ).first()
            if existing:
                remove_file(existing.id)

            dest = settings.uploads_dir / project_id / upload.filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(upload.file.read())

            source_path = f"{source_dir}/{upload.filename}" if source_dir else None
            file = File(
                project_id=project_id,
                file_name=upload.filename,
                file_path=str(dest),
                source_path=source_path,
                file_type=ext,
            )
            session.add(file)
            session.commit()
            session.refresh(file)
            background.add_task(ingest_file, file.id)
            out.append({"id": file.id, "file_name": file.file_name, "status": file.status.value})
    return out


@router.get("/projects/{project_id}/files/{file_id}/content")
def file_content(project_id: str, file_id: str) -> FileResponse:
    with get_session() as session:
        _get_project(session, project_id)
        file = session.get(File, file_id)
        if file is None or file.project_id != project_id:
            raise HTTPException(404, "File not found")
    path = Path(file.file_path)
    if not path.exists():
        raise HTTPException(404, "File content not found on disk")
    media_type = mimetypes.guess_type(file.file_name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media_type,
        filename=file.file_name,
        content_disposition_type="inline",
    )


@router.delete("/projects/{project_id}/files/{file_id}", status_code=204)
def delete_file(project_id: str, file_id: str) -> None:
    with get_session() as session:
        _get_project(session, project_id)
        file = session.get(File, file_id)
        if file is None or file.project_id != project_id:
            raise HTTPException(404, "File not found")
    remove_file(file_id)


@router.get("/projects/{project_id}/search")
def search(project_id: str, q: str = Query(...)) -> dict:
    q = q.strip()
    if not q:
        raise HTTPException(422, "Query must not be empty")
    if len(q) > settings.max_query_length:
        raise HTTPException(422, f"Query too long (max {settings.max_query_length} characters)")
    with get_session() as session:
        _get_project(session, project_id)
    return {"query": q, "results": retrieval.search(project_id, q)}


@router.get("/mcp-info")
def mcp_info() -> dict:
    # trailing slash required: the MCP sub-app is mounted at "/mcp" and only
    # matches its inner "/" route when the request path itself ends in "/"
    url = f"{settings.public_base_url.rstrip('/')}/mcp/"
    config = {"mcpServers": {"doc-kb": {"type": "http", "url": url}}}
    return {"url": url, "config_json": json.dumps(config, indent=2)}
