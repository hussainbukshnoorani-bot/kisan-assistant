"""Security finding F2: a contact sending too many messages stops getting replies.

Each reply costs money on WhatsApp and SMS, so a flood from one number must not be answered.
"""

from __future__ import annotations

import httpx
import respx
from sqlalchemy import Engine, text

from kisan.conversation.handler import RATE_LIMIT_PER_MINUTE
from tests.helpers import send_sms, send_whatsapp, sms_replies, whatsapp_replies


async def test_flood_from_one_number_is_capped(client: httpx.AsyncClient,
                                               whatsapp_api: respx.MockRouter,
                                               engine: Engine) -> None:
    for i in range(RATE_LIMIT_PER_MINUTE + 3):
        await send_whatsapp(client, "923001234567", "salam", msg_id=f"flood-{i}")
    assert len(whatsapp_replies(whatsapp_api)) == RATE_LIMIT_PER_MINUTE
    with engine.connect() as conn:
        limited = conn.execute(text(
            "SELECT count(*) FROM conversation_turns WHERE reply_type = 'rate_limited'"
        )).scalar_one()
    assert limited == 3


async def test_other_numbers_are_not_affected(client: httpx.AsyncClient, app,  # type: ignore[no-untyped-def]
                                              whatsapp_api: respx.MockRouter) -> None:
    for i in range(RATE_LIMIT_PER_MINUTE + 2):
        await send_whatsapp(client, "923001234567", "salam", msg_id=f"flood-{i}")
    await send_whatsapp(client, "923009999999", "salam", msg_id="other-1")
    await send_sms(client, "03001234567", "salam", msg_id="sms-1")  # same person, other channel
    assert len(whatsapp_replies(whatsapp_api)) == RATE_LIMIT_PER_MINUTE + 1
    assert len(sms_replies(app)) == 1
