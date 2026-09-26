import pytest
from pydantic import ValidationError

from kisan.config import Settings

BASE = {
    "database_url": "postgresql+psycopg://u:p@localhost/db",
    "contact_hash_pepper": "p" * 20,
    "sms_webhook_secret": "s" * 32,
}


def make(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**BASE, **overrides})  # type: ignore[arg-type]


def test_loads_required_values() -> None:
    s = make()
    assert s.database_url == BASE["database_url"]
    assert s.sms_provider == "fake"
    assert s.anthropic_api_key is None


@pytest.mark.parametrize("missing", ["database_url", "contact_hash_pepper", "sms_webhook_secret"])
def test_missing_required_value_raises(missing: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(missing.upper(), raising=False)
    values = {k: v for k, v in BASE.items() if k != missing}
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **values)  # type: ignore[arg-type]


def test_short_sms_secret_rejected() -> None:
    with pytest.raises(ValidationError):
        make(sms_webhook_secret="short")


def test_short_pepper_rejected() -> None:
    with pytest.raises(ValidationError):
        make(contact_hash_pepper="short")


def test_secrets_are_not_shown_in_repr() -> None:
    s = make(whatsapp_app_secret="top-secret-value")
    assert "top-secret-value" not in repr(s)


@pytest.mark.parametrize("url", [
    "postgres://u:p@host.neon.tech/db?sslmode=require",
    "postgresql://u:p@host.neon.tech/db?sslmode=require",
])
def test_hosted_postgres_urls_use_psycopg_driver(url: str) -> None:
    s = make(database_url=url)
    assert s.database_url == "postgresql+psycopg://u:p@host.neon.tech/db?sslmode=require"


def test_inline_replies_off_by_default() -> None:
    assert make().inline_replies is False
