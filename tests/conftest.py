"""Shared fixtures.

The database is real PostgreSQL: `TEST_DATABASE_URL` when set (CI), otherwise a throwaway
server started with pgserver (research R17).
"""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import httpx
import pytest
import respx
from sqlalchemy import Engine, create_engine, text

from kisan.config import Settings

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

TEST_PEPPER = "test-pepper-0123456789abcdef"
SMS_SECRET = "sms-secret-0123456789abcdef0123456789"
WA_APP_SECRET = "wa-app-secret"
WA_VERIFY_TOKEN = "wa-verify-token"
WA_PHONE_NUMBER_ID = "1234567890"
WA_API_BASE = "https://graph.test/v21.0"

MUTABLE_TABLES = ("conversation_turns", "pending_clarifications", "price_records")


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    url = os.environ.get("TEST_DATABASE_URL")
    if url:
        yield url
        return

    import pgserver

    pgdata = tempfile.mkdtemp(prefix="kisan-pg-")
    server = pgserver.get_server(pgdata, cleanup_mode="stop")
    server.psql("DROP DATABASE IF EXISTS kisan_test;")
    server.psql("CREATE DATABASE kisan_test;")
    yield server.get_uri("kisan_test").replace("postgresql://", "postgresql+psycopg://", 1)
    server.cleanup()
    shutil.rmtree(pgdata, ignore_errors=True)


@pytest.fixture(scope="session")
def migrated_engine(database_url: str) -> Iterator[Engine]:
    from kisan.db.migrate import upgrade
    from kisan.jobs.seed_reference import enable_fixture_source, seed_reference

    upgrade(database_url)
    engine = create_engine(database_url)
    seed_reference(engine, ROOT / "data" / "reference")
    enable_fixture_source(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def engine(migrated_engine: Engine) -> Engine:
    """Engine with conversation and price tables emptied before each test."""
    with migrated_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {', '.join(MUTABLE_TABLES)} RESTART IDENTITY CASCADE"))
        conn.execute(text("UPDATE price_sources SET consecutive_failures = 0"))
    return migrated_engine


@pytest.fixture
def settings(database_url: str) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url=database_url,
        contact_hash_pepper=TEST_PEPPER,
        whatsapp_app_secret=WA_APP_SECRET,
        whatsapp_verify_token=WA_VERIFY_TOKEN,
        whatsapp_access_token="wa-access-token",
        whatsapp_phone_number_id=WA_PHONE_NUMBER_ID,
        whatsapp_api_base=WA_API_BASE,
        sms_provider="fake",
        sms_webhook_secret=SMS_SECRET,
        reference_dir=ROOT / "data" / "reference",
        business_file=ROOT / "data" / "business.yaml",
    )


@pytest.fixture
def whatsapp_api() -> Iterator[respx.MockRouter]:
    """Stubs the WhatsApp send API; `whatsapp_api.calls` holds sent messages."""
    with respx.mock(base_url=WA_API_BASE, assert_all_called=False) as router:
        router.post(f"/{WA_PHONE_NUMBER_ID}/messages").mock(
            return_value=httpx.Response(200, json={"messages": [{"id": "wamid.out"}]})
        )
        yield router


@pytest.fixture
def app(settings: Settings, engine: Engine, whatsapp_api: respx.MockRouter):  # type: ignore[no-untyped-def]
    from kisan.app import create_app

    return create_app(settings)


@pytest.fixture
async def client(app) -> AsyncIterator[httpx.AsyncClient]:  # type: ignore[no-untyped-def]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
