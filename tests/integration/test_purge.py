"""T074 / research R12: conversation text kept 90 days; expired clarifications removed."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from kisan.conversation.clarification import save_pending
from kisan.jobs.purge import RETENTION_DAYS, purge

NOW = datetime(2026, 9, 27, 7, 0, tzinfo=UTC)


def _turn(engine: Engine, received_at: datetime) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO conversation_turns (id, provider_message_id, contact_hash, channel,"
            " received_at, message_text, script, understood_by, crop_ids, mandi_ids,"
            " price_record_ids, holding_message_sent)"
            " VALUES (:id, :pid, 'h', 'sms', :at, 'gandum multan', 'ur-Latn', 'dictionary',"
            " '{}', '{}', '{}', false)"
        ), {"id": uuid.uuid4(), "pid": str(uuid.uuid4()), "at": received_at})


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT count(*) FROM {table}")).scalar_one())


def test_old_turns_and_expired_clarifications_removed(engine: Engine) -> None:
    _turn(engine, NOW - timedelta(days=RETENTION_DAYS + 1))
    _turn(engine, NOW - timedelta(days=RETENTION_DAYS - 1))
    with Session(engine) as session:
        save_pending(session, "old", "sms", crop_id="wheat", mandi_id=None, awaiting="mandi",
                     script="ur-Latn", now=NOW - timedelta(hours=1))
        save_pending(session, "new", "sms", crop_id="wheat", mandi_id=None, awaiting="mandi",
                     script="ur-Latn", now=NOW)

    result = purge(engine, NOW)

    assert (result.turns, result.clarifications) == (1, 1)
    assert _count(engine, "conversation_turns") == 1
    assert _count(engine, "pending_clarifications") == 1


def test_nothing_to_purge(engine: Engine) -> None:
    result = purge(engine, NOW)
    assert (result.turns, result.clarifications) == (0, 0)
