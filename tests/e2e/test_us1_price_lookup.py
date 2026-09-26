"""US1: ask a crop price at a named mandi (spec acceptance scenarios 1-4 + edge cases)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, date, datetime

import httpx
import pytest
import respx
import time_machine
from sqlalchemy import Engine, text

from kisan.channels.sms import fits_sms
from tests.e2e.prices import add_price
from tests.helpers import send_sms, send_whatsapp, sms_replies, whatsapp_replies

pytestmark = pytest.mark.e2e

NOW = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)  # 12:00 PKT
YESTERDAY = date(2026, 9, 25)
WA_FROM = "923001234567"
SMS_FROM = "03001234567"


@pytest.fixture(autouse=True)
def frozen_time() -> Iterator[None]:
    with time_machine.travel(NOW, tick=True):
        yield


@pytest.fixture
def prices(engine: Engine) -> dict[str, int]:
    return {
        "wheat_multan": add_price(engine, "wheat", "multan", YESTERDAY, 3900, 4050),
        "wheat_lahore": add_price(engine, "wheat", "lahore", YESTERDAY, 4000, 4100),
        "cotton_multan": add_price(engine, "cotton", "multan", YESTERDAY, 8200, 8650),
        "maize_sahiwal": add_price(engine, "maize", "sahiwal", YESTERDAY, 2500, 2500),
    }


async def ask(client: httpx.AsyncClient, app, whatsapp_api: respx.MockRouter,  # type: ignore[no-untyped-def]
              channel: str, question: str) -> list[str]:
    if channel == "whatsapp":
        await send_whatsapp(client, WA_FROM, question)
        return whatsapp_replies(whatsapp_api)
    await send_sms(client, SMS_FROM, question)
    return sms_replies(app)


@pytest.mark.parametrize("channel", ["whatsapp", "sms"])
async def test_scenario_1_roman_urdu(client, app, whatsapp_api, prices, channel) -> None:  # type: ignore[no-untyped-def]
    replies = await ask(client, app, whatsapp_api, channel,
                        "Multan mandi mein gandum ka rate kya hai?")
    assert len(replies) == 1
    reply = replies[0]
    for part in ("Multan", "Gandum", "Rs 3,900-4,050", "40 kg", "Test data", "25 Sep"):
        assert part in reply, part


@pytest.mark.parametrize("channel", ["whatsapp", "sms"])
async def test_scenario_2_urdu_script(client, app, whatsapp_api, prices, channel) -> None:  # type: ignore[no-untyped-def]
    replies = await ask(client, app, whatsapp_api, channel, "ملتان منڈی میں گندم کا ریٹ کیا ہے؟")
    reply = replies[0]
    for part in ("ملتان", "گندم", "3,900", "4,050", "40 کلو", "ٹیسٹ ڈیٹا", "25 ستمبر"):
        assert part in reply, part
    assert "Multan" not in reply


async def test_scenario_3_single_price_not_range(client, app, whatsapp_api, prices) -> None:  # type: ignore[no-untyped-def]
    replies = await ask(client, app, whatsapp_api, "whatsapp", "sahiwal makai rate")
    assert "Rs 2,500 " in replies[0]
    assert "2,500-" not in replies[0]


@pytest.mark.parametrize("question", [
    "gehun ka bhao multan", "kanak multan", "wheat price in multan", "گندم ملتان",
    "Multan mandi gandam", "ملتان منڈی كنك",
])
async def test_scenario_4_spelling_variants(client, app, whatsapp_api, prices, question) -> None:  # type: ignore[no-untyped-def]
    replies = await ask(client, app, whatsapp_api, "whatsapp", question)
    assert "3,900" in replies[0]


async def test_several_pairs_on_whatsapp(client, app, whatsapp_api, prices) -> None:  # type: ignore[no-untyped-def]
    replies = await ask(client, app, whatsapp_api, "whatsapp", "gandum kapas multan lahore")
    reply = replies[0]
    assert "3,900" in reply and "4,000" in reply and "8,200" in reply
    assert len(reply) <= 480


async def test_several_pairs_on_urdu_sms_trimmed(client, app, whatsapp_api, prices) -> None:  # type: ignore[no-untyped-def]
    replies = await ask(client, app, whatsapp_api, "sms", "گندم کپاس ملتان لاہور")
    reply = replies[0]
    assert fits_sms(reply)
    assert "3,900" in reply
    assert "الگ پیغام" in reply  # "send the rest separately"


async def test_mixed_script_uses_majority(client, app, whatsapp_api, prices) -> None:  # type: ignore[no-untyped-def]
    replies = await ask(client, app, whatsapp_api, "whatsapp", "Multan منڈی میں گندم کا ریٹ")
    assert "ملتان" in replies[0]


async def test_voice_note_gets_text_only_reply(client, whatsapp_api, prices) -> None:  # type: ignore[no-untyped-def]
    await send_whatsapp(client, WA_FROM, None, kind="audio")
    replies = whatsapp_replies(whatsapp_api)
    assert len(replies) == 1
    assert "likha hua message" in replies[0]


async def test_turn_records_price_used(client, app, whatsapp_api, prices, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    await ask(client, app, whatsapp_api, "whatsapp", "multan gandum")
    with engine.connect() as conn:
        turn = conn.execute(text(
            "SELECT reply_type, crop_ids, mandi_ids, price_record_ids, understood_by, latency_ms"
            " FROM conversation_turns")).one()
    assert turn.reply_type == "price"
    assert turn.crop_ids == ["wheat"] and turn.mandi_ids == ["multan"]
    assert turn.price_record_ids == [prices["wheat_multan"]]
    assert turn.understood_by == "dictionary"
    assert turn.latency_ms is not None


async def test_rejected_price_never_shown(client, app, whatsapp_api, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    add_price(engine, "wheat", "multan", YESTERDAY, 0, 0, status="rejected",
              reject_reason="zero")
    replies = await ask(client, app, whatsapp_api, "whatsapp", "multan gandum")
    assert "Rs 0" not in replies[0]


async def test_disabled_source_prices_not_shown(client, app, whatsapp_api, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    add_price(engine, "wheat", "multan", YESTERDAY, 5555, 5555, source="amis_punjab")
    replies = await ask(client, app, whatsapp_api, "whatsapp", "multan gandum")
    assert "5,555" not in replies[0]


async def test_rice_word_answers_both_paddy_varieties(client, app, whatsapp_api,  # type: ignore[no-untyped-def]
                                                      engine: Engine) -> None:
    add_price(engine, "paddy_basmati", "gujranwala", YESTERDAY, 3800, 4400)
    add_price(engine, "paddy_irri", "gujranwala", YESTERDAY, 1400, 1500)
    replies = await ask(client, app, whatsapp_api, "whatsapp", "Gujranwala chawal ka rate")
    reply = replies[0]
    assert "Dhaan Basmati" in reply and "3,800" in reply
    assert "Dhaan IRRI" in reply and "1,400" in reply


async def test_variety_word_answers_one_variety(client, app, whatsapp_api,  # type: ignore[no-untyped-def]
                                                engine: Engine) -> None:
    add_price(engine, "paddy_basmati", "gujranwala", YESTERDAY, 3800, 4400)
    add_price(engine, "paddy_irri", "gujranwala", YESTERDAY, 1400, 1500)
    replies = await ask(client, app, whatsapp_api, "whatsapp", "گوجرانوالہ باسمتی")
    assert "دھان باسمتی" in replies[0] and "دھان اری" not in replies[0]


async def test_sugarcane_is_not_supported(client, app, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    replies = await ask(client, app, whatsapp_api, "whatsapp", "Rahim Yar Khan ganne ka rate")
    assert "shamil nahin" in replies[0]
