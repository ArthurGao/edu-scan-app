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

    # JWT
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # AI Providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    default_ai_provider: str = "claude"

    # OCR
    ocr_provider: str = "google"
    google_cloud_credentials_path: str = ""
    baidu_ocr_app_id: str = ""
    baidu_ocr_api_key: str = ""
    baidu_ocr_secret_key: str = ""

    # AWS S3
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "ap-southeast-2"
    s3_bucket_name: str = "eduscan-images"

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:19006"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
