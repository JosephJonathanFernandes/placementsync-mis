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


def validate_settings() -> None:
    """Validate required settings on startup.

    Raises a clear error if critical configuration is missing, so the app
    fails fast instead of producing confusing runtime errors later.
    """
    s = get_settings()
    issues: list[str] = []

    if not s.secret_key or s.secret_key == "change-me-in-production":
        issues.append("SECRET_KEY must be set to a secure value")

    if s.app_env == "production":
        if not s.google_client_id or not s.google_client_secret:
            issues.append("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET required in production")
        if s.debug:
            issues.append("DEBUG must be False in production")

    if issues:
        raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {i}" for i in issues))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
