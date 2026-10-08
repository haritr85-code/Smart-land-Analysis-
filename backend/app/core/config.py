"""
core/config.py
---------------
Centralized application configuration.

All environment-driven settings live here so the rest of the codebase
never touches `os.environ` directly. Values are loaded from a `.env`
file via pydantic-settings, validated, and cached as a singleton.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Strongly typed application settings.
    Supports standard single DATABASE_URL deployment environments (Render, Supabase, etc.).
    """

    # ---------------- App ----------------
    APP_NAME: str = "Smart Land Analysis Platform"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ---------------- Database ----------------
    DATABASE_URL_RAW: str = Field(
        default="postgresql+asyncpg://postgres:SmartLand%402026@localhost:5432/smart_land_db",
        validation_alias="DATABASE_URL",
    )
    DATABASE_URL_SYNC_RAW: str = Field(
        default="",
        validation_alias="DATABASE_URL_SYNC",
    )

    # ---------------- JWT ----------------
    JWT_SECRET_KEY: str = "smart-land-analysis-platform-secret-key-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ---------------- CORS ----------------
    BACKEND_CORS_ORIGINS_RAW: str = Field(default="", validation_alias="BACKEND_CORS_ORIGINS")

    # ---------------- Reports ----------------
    REPORTS_DIR: str = "generated_reports"

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL(self) -> str:
        """
        Normalized asyncpg database connection string.
        - Automatically converts postgres:// and postgresql:// to postgresql+asyncpg://
        - Strips accidental 'DATABASE_URL=' prefix or quotes if pasted into env value.
        - Strips query parameters unsupported by asyncpg (like ?sslmode=require).
        """
        raw = (self.DATABASE_URL_RAW or "").strip()
        if not raw:
            return ""

        # Defensively strip 'DATABASE_URL=' if accidentally pasted into env value field
        if raw.startswith("DATABASE_URL="):
            raw = raw[len("DATABASE_URL="):].strip()

        raw = raw.strip("\"'")

        if raw.startswith("postgres://"):
            raw = "postgresql+asyncpg://" + raw[len("postgres://"):]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+asyncpg://" + raw[len("postgresql://"):]
        elif not raw.startswith("postgresql+asyncpg://"):
            if "://" in raw:
                _, rest = raw.split("://", 1)
                raw = f"postgresql+asyncpg://{rest}"
            else:
                raw = f"postgresql+asyncpg://{raw}"

        # Clean query string parameters not recognized directly by asyncpg dialect
        if "?" in raw:
            base_url, query_str = raw.split("?", 1)
            params = [p for p in query_str.split("&") if p and not p.startswith("sslmode=")]
            raw = f"{base_url}?{'&'.join(params)}" if params else base_url

        return raw

    @computed_field  # type: ignore[misc]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """
        Normalized sync (psycopg2) database connection string for Alembic.
        Derived from DATABASE_URL_SYNC if set, or converted from DATABASE_URL.
        """
        raw = (self.DATABASE_URL_SYNC_RAW or "").strip()
        if not raw:
            raw = (self.DATABASE_URL_RAW or "").strip()

        if not raw:
            return ""

        if raw.startswith("DATABASE_URL_SYNC="):
            raw = raw[len("DATABASE_URL_SYNC="):].strip()
        elif raw.startswith("DATABASE_URL="):
            raw = raw[len("DATABASE_URL="):].strip()

        raw = raw.strip("\"'")

        if raw.startswith("postgres://"):
            raw = "postgresql+psycopg2://" + raw[len("postgres://"):]
        elif raw.startswith("postgresql+asyncpg://"):
            raw = "postgresql+psycopg2://" + raw[len("postgresql+asyncpg://"):]
        elif raw.startswith("postgresql://"):
            raw = "postgresql+psycopg2://" + raw[len("postgresql://"):]

        return raw

    def get_database_url(self, async_driver: bool = True) -> str:
        """Helper method for backwards compatibility."""
        return self.DATABASE_URL if async_driver else self.DATABASE_URL_SYNC

    @computed_field  # type: ignore[misc]
    @property
    def BACKEND_CORS_ORIGINS(self) -> List[str]:
        """Comma-separated env value, parsed into a clean list of origins."""
        raw = self.BACKEND_CORS_ORIGINS_RAW.strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
