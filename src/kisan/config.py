"""Settings loaded from environment variables (or a local .env file)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str
    contact_hash_pepper: SecretStr = Field(min_length=16)

    whatsapp_app_secret: SecretStr = SecretStr("")
    whatsapp_verify_token: SecretStr = SecretStr("")
    whatsapp_access_token: SecretStr = SecretStr("")
    whatsapp_phone_number_id: str = ""
    whatsapp_api_base: str = "https://graph.facebook.com/v21.0"

    sms_provider: Literal["fake"] = "fake"
    sms_webhook_secret: SecretStr = Field(min_length=32)

    anthropic_api_key: SecretStr | None = None

    # Crops, mandis, synonyms, sources (relative to the working directory by default)
    reference_dir: Path = Path("data/reference")
    # Illustrative prices for the development/demo "fixture" source
    sample_prices_file: Path = Path("data/sample_prices.yaml")

    # Bearer secret for the daily scheduled job (/jobs/daily); the route is off when unset.
    # Vercel Cron sends `Authorization: Bearer $CRON_SECRET` automatically.
    cron_secret: SecretStr | None = None

    # Serverless hosts (Vercel) may freeze a function once it responds, so replies must be
    # sent before the webhook returns instead of in a background task.
    inline_replies: bool = False

    @field_validator("database_url")
    @classmethod
    def _use_psycopg_driver(cls, url: str) -> str:
        """Hosted Postgres (e.g. Neon) gives postgres:// URLs; SQLAlchemy needs the driver."""
        for prefix in ("postgres://", "postgresql://"):
            if url.startswith(prefix):
                return "postgresql+psycopg://" + url[len(prefix):]
        return url
