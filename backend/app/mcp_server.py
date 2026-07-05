"""MCP server exposing the knowledge base to AI agents (streamable HTTP)."""

from mcp.server.fastmcp import FastMCP
from sqlmodel import func, select

from . import retrieval, vectorstore
from .config import settings
from .db import File, Project, get_session

mcp = FastMCP(
    "document-knowledge-base",
    instructions=(
        "Search a business document knowledge base. Use list_projects to discover "
        "projects, search_documents to find the most relevant files (with exact "
        "locations: page/slide/sheet/section/lines), and get_chunk_context to read "
        "the text surrounding a matched chunk."
    ),
    stateless_http=True,
    streamable_http_path="/",
)


def _project_by_name(name: str) -> Project:
    with get_session() as session:
        project = session.exec(select(Project).where(Project.name == name)).first()
        if project is None:
            names = [p.name for p in session.exec(select(Project)).all()]
            raise ValueError(f"Project '{name}' not found. Available projects: {names}")
        return project


@mcp.tool()
def list_projects() -> list[dict]:
    """List all knowledge-base projects and their indexed file counts."""
    with get_session() as session:
        projects = session.exec(select(Project)).all()
        counts = dict(
            session.exec(select(File.project_id, func.count()).group_by(File.project_id)).all()
        )
        return [{"name": p.name, "files": counts.get(p.id, 0)} for p in projects]


@mcp.tool()
def search_documents(query: str, project: str) -> dict:
    """Hybrid (keyword + semantic) search over a project's documents.

    Returns at most 3 relevant files, each with its best-matching chunks and their
    exact locations (page, slide, sheet, section path, line numbers) plus snippets.
    """
    query = query.strip()
    if not query:
        raise ValueError("Query must not be empty")
    if len(query) > settings.max_query_length:
        raise ValueError(f"Query too long (max {settings.max_query_length} characters)")
    p = _project_by_name(project)
    return {"query": query, "results": retrieval.search(p.id, query)}


@mcp.tool()
def get_chunk_context(project: str, chunk_id: str) -> dict:
    """Fetch a chunk by id together with its previous and next chunks in the file."""
    p = _project_by_name(project)
    name = vectorstore.collection_name(p.id)
    client = vectorstore.client()

    def fetch(cid: str | None) -> dict | None:
        if not cid:
            return None
        pts = client.retrieve(name, ids=[cid], with_payload=True)
        if not pts:
            return None
        pl = pts[0].payload
        return {k: pl.get(k) for k in ("id", "text", "section_path", "page", "slide", "sheet", "line_start", "line_end", "prev_chunk_id", "next_chunk_id")}

    chunk = fetch(chunk_id)
    if chunk is None:
        raise ValueError(f"Chunk '{chunk_id}' not found in project '{project}'")
    return {
        "prev": fetch(chunk.get("prev_chunk_id")),
        "chunk": chunk,
        "next": fetch(chunk.get("next_chunk_id")),
    }
