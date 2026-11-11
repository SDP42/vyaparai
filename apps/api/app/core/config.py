"""Application settings loaded from environment variables (and an optional .env file)."""

from functools import lru_cache
from typing import Literal, Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_JWT_SECRET = "dev-only-insecure-secret-change-me-0123456789"  # noqa: S105 - dev placeholder


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Vyapar AI API"
    app_version: str = "0.1.0"
    app_env: Literal["development", "test", "production"] = "development"
    api_v1_prefix: str = "/api/v1"

    database_url: str = "sqlite:///./vyapar_dev.db"
    database_echo: bool = False

    jwt_secret_key: str = DEV_JWT_SECRET
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    # Hardening (Phase 11)
    redis_url: str | None = None  # shared rate-limit store; without it limits are per process
    trust_proxy: bool = (
        False  # read the client address from X-Forwarded-For (only behind a proxy you control)
    )
    rate_limit_per_minute: int = 600  # all requests per address
    heavy_rate_limit_per_minute: int = 60  # uploads, search, questions, investigations, reports
    max_json_body_kb: int = 1024
    max_upload_body_mb: int = 20
    db_statement_timeout_ms: int = 15000  # PostgreSQL only: the hard stop for a slow query
    db_pool_size: int = 10
    db_max_overflow: int = 10
    campaign_daily_cap: int = (
        100  # messages a person may send from one workspace in a day, to keep it polite
    )
    refresh_token_days: int = 14  # idle timeout: each refresh extends it
    session_max_days: int = 30  # absolute timeout for one sign-in, however active
    refresh_cookie_name: str = "vyapar_refresh"
    login_failures_per_window: int = 5
    login_window_seconds: int = 900
    register_per_hour_per_ip: int = 10

    cors_origins: list[str] = ["http://localhost:3000"]

    log_level: str = "INFO"
    log_json: bool = True

    max_upload_size_mb: int = 25
    max_upload_rows: int = 200_000
    storage_dir: str = "./storage"

    # Weather signal (docs/research/EXTERNAL-FACTORS.md). Open-Meteo's free endpoint is for
    # non-commercial use only, so production refuses it unless a paid key is configured.
    weather_enabled: bool = True
    # Voice (speech to text on this server; audio is never stored)
    voice_enabled: bool = True
    voice_warm_start: bool = (
        True  # load the speech model at startup so the first question is not slow
    )
    stt_model: str = "medium"  # Whisper size or a local folder: tiny, base, small, medium
    stt_compute_type: str = "int8"
    stt_cpu_threads: int = 4
    stt_local_files_only: bool = False  # true on a server that must never fetch weights
    voice_max_seconds: int = 15
    voice_max_audio_kb: int = 1024
    open_meteo_api_key: str | None = None
    weather_timeout_seconds: float = 8.0

    # Link sources (scheduled imports). Only these hosts may be fetched unless an admin opens it up.
    source_allowed_hosts: list[str] = [
        "docs.google.com", "drive.google.com", "*.googleusercontent.com",
        "dl.dropboxusercontent.com", "dl.dropbox.com", "raw.githubusercontent.com",
    ]  # fmt: skip
    source_allow_any_public_host: bool = False
    source_fetch_timeout_seconds: float = 20.0
    max_sources_per_workspace: int = 5

    # Owner digest email. Disabled until an SMTP host is configured; the text can always be copied.
    app_url: str = "http://localhost:3000"
    demo_login_enabled: bool = False  # one-tap sample accounts per persona; never in production
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str = "Vyapar AI <no-reply@localhost>"
    smtp_starttls: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def weather_allowed(self) -> bool:
        """Free tier only outside production; production needs a paid key (licence rule)."""
        return self.weather_enabled and (not self.is_production or bool(self.open_meteo_api_key))

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> Self:
        if self.is_production:
            if self.demo_login_enabled:
                raise ValueError("DEMO_LOGIN_ENABLED must be off in production")
            if self.jwt_secret_key == DEV_JWT_SECRET or len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must be set to a random value of 32+ chars")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production must use PostgreSQL, not SQLite")
            if any(not o.startswith("https://") for o in self.cors_origins):
                raise ValueError("Production CORS_ORIGINS must all be https:// addresses")
            if not self.app_url.startswith("https://"):
                raise ValueError("Production APP_URL must be an https:// address")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
