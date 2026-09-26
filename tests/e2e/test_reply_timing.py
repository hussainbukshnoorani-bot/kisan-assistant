"""FR-013 / research R11: holding message after a delay, give up before the time limit."""

from __future__ import annotations

import time
from datetime import UTC, date, datetime

import pytest
import time_machine
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from tests.e2e.prices import add_price
from tests.helpers import send_whatsapp, whatsapp_replies

pytestmark = pytest.mark.e2e

NOW = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)


def _slow(handler, seconds: float) -> None:  # type: ignore[no-untyped-def]
    original = handler._decide

    def slow_decide(*args, **kwargs):  # type: ignore[no-untyped-def]
        time.sleep(seconds)
        return original(*args, **kwargs)

    handler._decide = slow_decide


@pytest.fixture
def handler(app, engine: Engine):  # type: ignore[no-untyped-def]
    add_price(engine, "wheat", "multan", date(2026, 9, 25), 3900, 4050)
    h = app.state.services.handler
    h.holding_after = 0.1
    h.give_up_after = 0.6
    return h


@time_machine.travel(NOW, tick=True)
async def test_fast_answer_has_no_holding_message(client, whatsapp_api, handler) -> None:  # type: ignore[no-untyped-def]
    await send_whatsapp(client, "923001234567", "multan gandum")
    replies = whatsapp_replies(whatsapp_api)
    assert len(replies) == 1 and "3,900" in replies[0]


@time_machine.travel(NOW, tick=True)
async def test_slow_answer_sends_holding_message_first(client, whatsapp_api, handler,  # type: ignore[no-untyped-def]
                                                       engine: Engine) -> None:
    _slow(handler, 0.3)
    await send_whatsapp(client, "923001234567", "multan gandum")
    replies = whatsapp_replies(whatsapp_api)
    assert len(replies) == 2
    assert "intezar" in replies[0]
    assert "3,900" in replies[1]
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT holding_message_sent FROM conversation_turns")).scalar_one() is True


@time_machine.travel(NOW, tick=True)
async def test_too_slow_gives_up_with_source_down(client, whatsapp_api, handler,  # type: ignore[no-untyped-def]
                                                  engine: Engine) -> None:
    _slow(handler, 1.5)
    await send_whatsapp(client, "923001234567", "multan gandum")
    replies = whatsapp_replies(whatsapp_api)
    assert len(replies) == 2
    assert "dobara" in replies[1]
    with engine.connect() as conn:
        assert conn.execute(text(
            "SELECT reply_type FROM conversation_turns")).scalar_one() == "source_down"


@time_machine.travel(NOW, tick=True)
async def test_database_error_gives_source_down(client, whatsapp_api, handler) -> None:  # type: ignore[no-untyped-def]
    def broken(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OperationalError("SELECT 1", {}, Exception("connection lost"))

    handler._decide = broken
    await send_whatsapp(client, "923001234567", "multan gandum")
    replies = whatsapp_replies(whatsapp_api)
    assert len(replies) == 1
    assert "dobara" in replies[0]
