"""Contract: GET /health per contracts/webhooks.openapi.yaml."""

from datetime import UTC, date, datetime, timedelta

import httpx
import time_machine
from sqlalchemy import Engine, text

TODAY = date(2026, 9, 26)
NOW = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)  # 12:00 in Asia/Karachi


def _insert_price(engine: Engine, price_date: date) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO price_records (source_id, crop_id, mandi_id, price_date, min_rs_40kg,"
            " max_rs_40kg, original_unit, fetched_at, status)"
            " VALUES ('fixture', 'wheat', 'multan', :d, 3900, 4050, 'per_40kg', now(), 'valid')"
        ), {"d": price_date})


@time_machine.travel(NOW, tick=False)
async def test_ok_with_recent_prices(client: httpx.AsyncClient, engine: Engine) -> None:
    _insert_price(engine, TODAY - timedelta(days=1))
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "ok",
                        "newest_price_date": (TODAY - timedelta(days=1)).isoformat()}


@time_machine.travel(NOW, tick=False)
async def test_degraded_when_prices_older_than_three_days(client: httpx.AsyncClient,
                                                          engine: Engine) -> None:
    _insert_price(engine, TODAY - timedelta(days=4))
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "degraded"


async def test_degraded_when_no_prices(client: httpx.AsyncClient) -> None:
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "degraded", "database": "ok", "newest_price_date": None}


async def test_down_when_database_unreachable(settings, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    from kisan.app import create_app

    broken = settings.model_copy(
        update={"database_url": "postgresql+psycopg://nobody:x@127.0.0.1:1/none"})
    app = create_app(broken)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 503
    assert r.json() == {"status": "down", "database": "down", "newest_price_date": None}
