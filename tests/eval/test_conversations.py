"""SC-006: incomplete questions resolved to the correct price within two bot messages (>= 85%).

Runs each conversation through the real webhook, database, and handler.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
import time_machine
import yaml
from sqlalchemy import Engine, text

from tests.e2e.prices import add_price
from tests.helpers import send_sms

pytestmark = pytest.mark.eval

HERE = Path(__file__).resolve().parent
NOW = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)
PRICE_DAY = date(2026, 9, 25)
SC006_MIN = 0.85


def _cases() -> list[dict[str, Any]]:
    return list(yaml.safe_load((HERE / "conversations.yaml").read_text(encoding="utf-8"))
                ["conversations"])


def _resolved(engine: Engine, record_ids: dict[tuple[str, str], int],
              expect: dict[str, str], bot_messages: int) -> bool:
    with engine.connect() as conn:
        turns = conn.execute(text(
            "SELECT reply_type, price_record_ids FROM conversation_turns ORDER BY received_at"
        )).all()
    wanted = record_ids[(expect["crop"], expect["mandi"])]
    for turn in turns[:bot_messages]:
        if turn.reply_type == "price":
            return wanted in turn.price_record_ids
    return False


async def test_sc006_incomplete_questions_resolved_within_two_messages(
        client, app, engine: Engine) -> None:  # type: ignore[no-untyped-def]
    cases = _cases()
    passed = 0
    failures: list[str] = []
    for i, case in enumerate(cases):
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE conversation_turns, pending_clarifications, "
                              "price_records RESTART IDENTITY"))
        pairs = {(c, m) for c in ("wheat", "cotton", "maize", "paddy_basmati")
                 for m in ("multan", "lahore", "sahiwal", "gujranwala", "faisalabad")}
        record_ids = {pair: add_price(engine, pair[0], pair[1], PRICE_DAY, 4000, 4100)
                      for pair in pairs}
        with time_machine.travel(NOW, tick=True):
            for j, message in enumerate(case["messages"]):
                await send_sms(client, f"0300{1000000 + i:07d}", message, msg_id=f"c{i}-{j}")
        if _resolved(engine, record_ids, case["expect"], bot_messages=2):
            passed += 1
        else:
            failures.append(" -> ".join(case["messages"]))

    rate = passed / len(cases)
    print(f"\nSC-006 incomplete questions resolved within 2 messages: {rate:.0%} "
          f"({passed}/{len(cases)})")
    for failure in failures:
        print("  FAIL", failure)
    assert rate >= SC006_MIN
