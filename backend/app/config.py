from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "EduScan"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/eduscan"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI Providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    default_ai_provider: str = "claude"

    # OCR
    ocr_provider: str = "gemini"
    google_cloud_credentials_path: str = ""
    baidu_ocr_app_id: str = ""
    baidu_ocr_api_key: str = ""
    baidu_ocr_secret_key: str = ""

    # Cloudflare R2 (S3-compatible)
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "eduscan"
    r2_public_url: str = ""  # Public access URL for the bucket

    # Model Configuration
    strong_model_claude: str = "claude-sonnet-4-20250514"
    fast_model_claude: str = "claude-haiku-4-5-20251001"
    strong_model_openai: str = "gpt-4o"
    fast_model_openai: str = "gpt-4o-mini"
    strong_model_gemini: str = "gemini-2.5-flash"
    fast_model_gemini: str = "gemini-2.5-flash-lite"

    # Embeddings
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # LangGraph
    max_solve_attempts: int = 3
    min_quality_score: float = 0.7

    # Conversation
    max_followup_messages: int = 20
    conversation_ttl_hours: int = 24

    # Observability (optional)
    langsmith_api_key: str = ""
    langsmith_project: str = "eduscan"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:19006"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
