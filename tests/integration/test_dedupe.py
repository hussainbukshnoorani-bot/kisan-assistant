"""FR-019: a repeated delivery gets exactly one reply."""

import httpx
import respx
from sqlalchemy import Engine, text

from tests.helpers import send_sms, send_whatsapp, sms_replies, whatsapp_replies


async def test_repeated_whatsapp_delivery_replied_once(client: httpx.AsyncClient,
                                                       whatsapp_api: respx.MockRouter,
                                                       engine: Engine) -> None:
    await send_whatsapp(client, "923001234567", "salam", msg_id="wamid.same")
    await send_whatsapp(client, "923001234567", "salam", msg_id="wamid.same")
    assert len(whatsapp_replies(whatsapp_api)) == 1
    with engine.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM conversation_turns")).scalar_one() == 1


async def test_same_id_on_other_channel_is_a_different_message(
        client: httpx.AsyncClient, whatsapp_api: respx.MockRouter, app) -> None:  # type: ignore[no-untyped-def]
    await send_whatsapp(client, "923001234567", "salam", msg_id="id-1")
    await send_sms(client, "03001234567", "salam", msg_id="id-1")
    assert len(whatsapp_replies(whatsapp_api)) == 1
    assert len(sms_replies(app)) == 1
