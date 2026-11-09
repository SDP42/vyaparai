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
    access_token_expire_minutes: int = 30

    cors_origins: list[str] = ["http://localhost:3000"]

    log_level: str = "INFO"
    log_json: bool = True

    max_upload_size_mb: int = 25
    max_upload_rows: int = 200_000
    storage_dir: str = "./storage"

    # Weather signal (docs/research/EXTERNAL-FACTORS.md). Open-Meteo's free endpoint is for
    # non-commercial use only, so production refuses it unless a paid key is configured.
    weather_enabled: bool = True
    open_meteo_api_key: str | None = None
    weather_timeout_seconds: float = 8.0

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
            if self.jwt_secret_key == DEV_JWT_SECRET or len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must be set to a random value of 32+ chars")
            if self.database_url.startswith("sqlite"):
                raise ValueError("Production must use PostgreSQL, not SQLite")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
