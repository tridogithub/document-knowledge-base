from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # OpenAI-compatible embedding endpoint
    embedding_base_url: str = "https://api.openai.com/v1"
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_batch_size: int = 64

    qdrant_url: str = "http://localhost:6333"

    # Where uploaded files and the SQLite registry live
    data_dir: Path = Path("./data")

    max_query_length: int = 512
    top_k_files: int = 3

    # Public base URL of this app, used for the MCP config snippet
    public_base_url: str = "http://localhost:8000"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "registry.db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"


settings = Settings()
settings.uploads_dir.mkdir(parents=True, exist_ok=True)
