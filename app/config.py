import functools
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["dev", "test", "production"] = "dev"
    secret_key: str = Field(min_length=32)
    database_url: str
    database_test_url: str | None = None

    upload_dir: Path
    backup_dir: Path
    log_dir: Path

    session_cookie_name: str = "cdsid"
    session_max_age_days: int = 30
    cookie_secure: bool = True

    vapid_public_key: str | None = None
    vapid_private_key: str | None = None
    vapid_subject: str | None = None

    @field_validator("upload_dir", "backup_dir", "log_dir")
    @classmethod
    def must_be_absolute(cls, v: Path) -> Path:
        # Treat as absolute if it has a drive (Windows) or a root (POSIX-style).
        # On Windows, Path("/tmp/x").is_absolute() is False (no drive), but
        # such paths are rooted and acceptable for our purposes.
        if not (v.is_absolute() or v.root):
            raise ValueError(f"must be absolute path, got {v}")
        return v


@functools.cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
