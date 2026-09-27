"""Daily scheduled job (Vercel Cron): refresh prices from enabled sources and purge old data.

Vercel calls the path with `Authorization: Bearer <CRON_SECRET>`.
"""

from __future__ import annotations

import httpx
from sqlalchemy import Engine, text

CRON_SECRET = "cron-secret-0123456789abcdef"


async def _get(app, headers: dict[str, str] | None = None) -> httpx.Response:  # type: ignore[no-untyped-def]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        return await c.get("/jobs/daily", headers=headers or {})


def _app(settings, cron_secret: str | None):  # type: ignore[no-untyped-def]
    from kisan.app import create_app

    return create_app(settings.model_copy(update={"cron_secret": cron_secret}))


async def test_disabled_when_no_secret_configured(settings, engine, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    r = await _get(_app(settings, None), {"Authorization": "Bearer anything"})
    assert r.status_code == 404


async def test_rejects_missing_or_wrong_secret(settings, engine, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    from pydantic import SecretStr

    app = _app(settings, SecretStr(CRON_SECRET))
    assert (await _get(app)).status_code == 401
    assert (await _get(app, {"Authorization": "Bearer wrong"})).status_code == 401


async def test_refreshes_enabled_sources_and_purges(settings, engine: Engine,  # type: ignore[no-untyped-def]
                                                    whatsapp_api) -> None:
    from pydantic import SecretStr

    app = _app(settings, SecretStr(CRON_SECRET))
    r = await _get(app, {"Authorization": f"Bearer {CRON_SECRET}"})

    assert r.status_code == 200
    body = r.json()
    assert body["sources"]["fixture"]["valid"] == 8
    assert body["sources"]["amis_punjab"] == "skipped (disabled)"
    assert body["purged"] == {"turns": 0, "clarifications": 0}
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM price_records")).scalar_one() == 8
