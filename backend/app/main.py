from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import router
from .db import init_db
from .mcp_server import mcp

STATIC_DIR = Path(__file__).parent / "static"

mcp_app = mcp.streamable_http_app()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    async with mcp.session_manager.run():
        yield


app = FastAPI(title="Document Knowledge Base", lifespan=lifespan)
app.include_router(router)
app.mount("/mcp", mcp_app)

if STATIC_DIR.is_dir():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="ui")
