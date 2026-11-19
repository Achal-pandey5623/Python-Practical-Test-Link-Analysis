from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    llm_provider: str = "google-ai-studio"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.8-flash"
    llm_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    llm_timeout_seconds: float = 180
    max_page_bytes: int = 2_000_000
    max_content_chars: int = 18_000
    cache_ttl_seconds: int = 900
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
