"""US2: honest answers when data is missing or old (spec acceptance scenarios 1-4)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
import time_machine
from sqlalchemy import Engine, text

from kisan.channels.sms import fits_sms
from tests.e2e.prices import add_price
from tests.helpers import send_sms, send_whatsapp, sms_replies, whatsapp_replies

pytestmark = pytest.mark.e2e

NOW = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)
TODAY = date(2026, 9, 26)


@pytest.fixture(autouse=True)
def frozen_time() -> Iterator[None]:
    with time_machine.travel(NOW, tick=True):
        yield


def _reply_type(engine: Engine) -> str:
    with engine.connect() as conn:
        return str(conn.execute(text(
            "SELECT reply_type FROM conversation_turns ORDER BY received_at DESC LIMIT 1"
        )).scalar_one())


async def test_scenario_1_no_price_no_figure(client, whatsapp_api, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    await send_whatsapp(client, "923001234567", "Multan gandum rate")
    reply = whatsapp_replies(whatsapp_api)[0]
    assert "maujood nahin" in reply
    assert "Rs" not in reply and not any(ch.isdigit() for ch in reply)
    assert _reply_type(engine) == "no_price"


async def test_scenario_2_stale_price_labelled_with_date(client, whatsapp_api,  # type: ignore[no-untyped-def]
                                                         engine: Engine) -> None:
    add_price(engine, "wheat", "multan", TODAY - timedelta(days=5), 3700, 3800)
    await send_whatsapp(client, "923001234567", "Multan gandum rate")
    reply = whatsapp_replies(whatsapp_api)[0]
    assert "21 Sep" in reply
    assert "taaza nahin" in reply
    assert "3,700" in reply
    assert _reply_type(engine) == "price_stale"


async def test_scenario_2_stale_in_urdu(client, app, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    add_price(engine, "wheat", "multan", TODAY - timedelta(days=5), 3700, 3800)
    await send_sms(client, "03001234567", "ملتان گندم ریٹ")
    reply = sms_replies(app)[0]
    assert "21 ستمبر" in reply and "تازہ نہیں" in reply
    assert fits_sms(reply)


async def test_scenario_3_neighbouring_mandi_named(client, whatsapp_api, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    add_price(engine, "wheat", "bahawalpur", TODAY - timedelta(days=1), 3850, 3950)
    await send_whatsapp(client, "923001234567", "Multan gandum rate")
    reply = whatsapp_replies(whatsapp_api)[0]
    assert "Multan" in reply and "Bahawalpur" in reply
    assert "3,850" in reply
    assert _reply_type(engine) == "price_other_mandi"


async def test_scenario_3_longest_urdu_sms_fits(client, app, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    add_price(engine, "maize", "bahawalpur", TODAY - timedelta(days=1), 10000, 12500)
    await send_sms(client, "03001234567", "رحیم یار خان مکئی")
    reply = sms_replies(app)[0]
    assert "بہاولپور" in reply
    assert fits_sms(reply)


async def test_scenario_4_database_unavailable(settings, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    import httpx

    from kisan.app import create_app

    broken = settings.model_copy(
        update={"database_url": "postgresql+psycopg://nobody:x@127.0.0.1:1/none"})
    app = create_app(broken)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        await send_whatsapp(c, "923001234567", "Multan gandum rate")
    replies = whatsapp_replies(whatsapp_api)
    assert len(replies) == 1
    assert "dobara" in replies[0]


async def test_invalid_price_never_shown(client, whatsapp_api, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    add_price(engine, "wheat", "multan", TODAY, 1, 1, status="rejected",
              reject_reason="out_of_range")
    await send_whatsapp(client, "923001234567", "Multan gandum rate")
    reply = whatsapp_replies(whatsapp_api)[0]
    assert "Rs 1 " not in reply
    assert _reply_type(engine) == "no_price"
