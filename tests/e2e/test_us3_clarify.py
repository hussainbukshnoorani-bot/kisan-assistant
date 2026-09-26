"""US3: clarify incomplete or ambiguous questions (spec acceptance scenarios 1-3 + edge cases)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import pytest
import time_machine
from sqlalchemy import Engine

from kisan.channels.sms import fits_sms
from tests.e2e.prices import add_price
from tests.helpers import send_sms, send_whatsapp, sms_replies, whatsapp_replies

pytestmark = pytest.mark.e2e

NOW = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)
WA = "923001234567"


@pytest.fixture(autouse=True)
def prices(engine: Engine) -> None:
    add_price(engine, "wheat", "multan", date(2026, 9, 25), 3900, 4050)


async def test_scenario_1_crop_only_then_mandi(client, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    with time_machine.travel(NOW, tick=True):
        await send_whatsapp(client, WA, "gandum ka rate?")
        await send_whatsapp(client, WA, "Multan")
    first, second = whatsapp_replies(whatsapp_api)
    assert "kis mandi" in first and "Gandum" in first
    assert "3,900" in second


async def test_scenario_2_mandi_only_then_crop_urdu(client, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    with time_machine.travel(NOW, tick=True):
        await send_whatsapp(client, WA, "ملتان منڈی کا ریٹ")
        await send_whatsapp(client, WA, "گندم")
    first, second = whatsapp_replies(whatsapp_api)
    assert "کس فصل" in first and "ملتان" in first
    assert "3,900" in second and "گندم" in second


@pytest.mark.parametrize("text", ["salam", "cricket ka score kya hai", "السلام علیکم"])
async def test_scenario_3_off_topic_gets_help(client, whatsapp_api, text) -> None:  # type: ignore[no-untyped-def]
    await send_whatsapp(client, WA, text)
    replies = whatsapp_replies(whatsapp_api)
    assert len(replies) == 1
    assert "Multan" in replies[0] or "ملتان" in replies[0]  # contains an example question


async def test_exactly_one_question_asked(client, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    await send_whatsapp(client, WA, "gandum ka rate?")
    assert len(whatsapp_replies(whatsapp_api)) == 1


async def test_pending_expires_after_30_minutes(client, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    with time_machine.travel(NOW, tick=False):
        await send_whatsapp(client, WA, "gandum ka rate?")
    with time_machine.travel(NOW + timedelta(minutes=31), tick=False):
        await send_whatsapp(client, WA, "Multan")
    second = whatsapp_replies(whatsapp_api)[1]
    assert "kis fasal" in second  # the earlier crop was forgotten, so it asks for the crop


async def test_complete_new_question_replaces_pending(client, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    with time_machine.travel(NOW, tick=True):
        await send_whatsapp(client, WA, "kapas ka rate?")
        await send_whatsapp(client, WA, "Multan gandum")
    assert "3,900" in whatsapp_replies(whatsapp_api)[1]


async def test_channel_switch_does_not_carry_over(client, app, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    with time_machine.travel(NOW, tick=True):
        await send_whatsapp(client, WA, "gandum ka rate?")
        await send_sms(client, "03001234567", "Multan")
    sms_reply = sms_replies(app)[0]
    assert "kis fasal" in sms_reply


@pytest.mark.parametrize("text", ["Quetta mandi seb ka rate", "کوئٹہ منڈی سیب کا ریٹ"])
async def test_unsupported_crop_or_mandi(client, whatsapp_api, text) -> None:  # type: ignore[no-untyped-def]
    await send_whatsapp(client, WA, text)
    reply = whatsapp_replies(whatsapp_api)[0]
    assert "shamil nahin" in reply or "شامل نہیں" in reply


async def test_list_of_mandis(client, app) -> None:  # type: ignore[no-untyped-def]
    await send_sms(client, "03001234567", "mandiyan")
    reply = sms_replies(app)[0]
    for name in ("Lahore", "Multan", "Rahim Yar Khan", "Sargodha"):
        assert name in reply
    assert fits_sms(reply)


async def test_list_of_crops_urdu(client, app) -> None:  # type: ignore[no-untyped-def]
    await send_sms(client, "03001234567", "فصلیں")
    reply = sms_replies(app)[0]
    for name in ("گندم", "کپاس", "دھان باسمتی", "دھان اری", "مکئی"):
        assert name in reply


async def test_full_list_roman_sms_has_both(client, app) -> None:  # type: ignore[no-untyped-def]
    await send_sms(client, "03001234567", "list")
    reply = sms_replies(app)[0]
    assert "Multan" in reply and "Gandum" in reply
    assert fits_sms(reply)


async def test_full_list_urdu_sms_falls_back_to_hint(client, app) -> None:  # type: ignore[no-untyped-def]
    await send_sms(client, "03001234567", "فہرست")
    reply = sms_replies(app)[0]
    assert "رحیم یار خان" in reply
    assert "فصلیں" in reply  # tells the farmer how to ask for crops
    assert fits_sms(reply)


async def test_full_list_urdu_whatsapp_has_both(client, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    await send_whatsapp(client, WA, "فہرست")
    reply = whatsapp_replies(whatsapp_api)[0]
    assert "رحیم یار خان" in reply and "مکئی" in reply
