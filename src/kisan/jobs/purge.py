"""Delete conversation turns older than 90 days and expired clarifications (research R12).

Usage: python -m kisan.jobs.purge  (also run by the daily scheduled job)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, delete
from sqlalchemy.orm import Session

from kisan.conversation.clarification import purge_expired
from kisan.db.models import ConversationTurn
from kisan.observability import get_logger

RETENTION_DAYS = 90
log = get_logger(__name__)


@dataclass(frozen=True)
class PurgeResult:
    turns: int
    clarifications: int


def purge(engine: Engine, now: datetime) -> PurgeResult:
    with Session(engine) as session:
        turns = session.execute(delete(ConversationTurn).where(
            ConversationTurn.received_at < now - timedelta(days=RETENTION_DAYS)))
        session.commit()
        clarifications = purge_expired(session, now)
    result = PurgeResult(int(turns.rowcount), clarifications)  # type: ignore[attr-defined]
    log.info("purge_completed", turns=result.turns, clarifications=result.clarifications)
    return result


def main() -> None:
    from kisan.config import Settings
    from kisan.db import make_engine
    from kisan.observability import configure_logging

    configure_logging()
    settings = Settings()  # type: ignore[call-arg]
    purge(make_engine(settings.database_url), datetime.now(UTC))


if __name__ == "__main__":
    main()
