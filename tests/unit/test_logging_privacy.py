"""Principle IV / FR-018: logs never contain phone numbers or message text."""

import httpx
import respx
from sqlalchemy import Engine, text
from structlog.contextvars import merge_contextvars
from structlog.testing import capture_logs

from tests.helpers import send_sms, send_whatsapp

MESSAGE = "salam mera number 0300-7654321 aur CNIC 35202-1234567-1 hai"


def _all_values(events: list[dict[str, object]]) -> str:
    return " ".join(str(v) for event in events for v in event.values())


async def test_logs_do_not_contain_number_or_text(client: httpx.AsyncClient,
                                                  whatsapp_api: respx.MockRouter) -> None:
    with capture_logs(processors=[merge_contextvars]) as events:
        await send_whatsapp(client, "923001234567", MESSAGE)
        await send_sms(client, "03009876543", MESSAGE)
    logged = _all_values(events)
    assert events, "expected some log events"
    for secret in ("3001234567", "3009876543", "7654321", "35202", MESSAGE):
        assert secret not in logged
    assert any("conversation_id" in e for e in events)


async def test_stored_text_is_redacted(client: httpx.AsyncClient,
                                       whatsapp_api: respx.MockRouter, engine: Engine) -> None:
    await send_whatsapp(client, "923001234567", MESSAGE)
    with engine.connect() as conn:
        stored = conn.execute(text("SELECT message_text FROM conversation_turns")).scalar_one()
    assert stored == "salam mera number [PHONE] aur CNIC [CNIC] hai"
