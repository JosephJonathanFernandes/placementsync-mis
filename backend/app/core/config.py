"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "PlacementSync"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    database_url: str = "sqlite:///./placement_sync.db"

    excel_file_path: str = "./exports/placement_register.xlsx"

    academic_year: str = "2024-25"

    # Gmail OAuth (Phase 2)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/auth/gmail/callback"
    frontend_url: str = "http://localhost:5173"

    # Optional LLM extraction provider (not required for core operation)
    llm_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    log_level: str = "INFO"
    log_file: str = "./logs/placement_sync.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
