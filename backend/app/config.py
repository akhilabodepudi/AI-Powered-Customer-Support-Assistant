from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_path: str = "data/support.db"
    frontend_origin: str = "http://localhost:5173"
    admin_api_key: str = "change-me-before-deploying"
    ai_provider: str = "local"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    top_k: int = 4
    min_retrieval_score: float = 0.12
    max_context_chars: int = 12000
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    def ensure_paths(self) -> None:
        path = Path(self.database_path)
        path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_paths()
    return settings

