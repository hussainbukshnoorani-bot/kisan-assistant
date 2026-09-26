"""Half-understood questions awaiting one more answer (FR-009, data-model PendingClarification).

State is kept per (contact_hash, channel), so WhatsApp and SMS never share it.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from kisan.db.models import PendingClarification

CLARIFY_MINUTES = 30


def get_pending(session: Session, contact_hash: str, channel: str,
                now: datetime) -> PendingClarification | None:
    return session.scalar(select(PendingClarification).where(
        PendingClarification.contact_hash == contact_hash,
        PendingClarification.channel == channel,
        PendingClarification.expires_at > now,
    ))


def save_pending(session: Session, contact_hash: str, channel: str, *, crop_id: str | None,
                 mandi_id: str | None, awaiting: Literal["crop", "mandi"], script: str,
                 now: datetime) -> None:
    values = {"crop_id": crop_id, "mandi_id": mandi_id, "awaiting": awaiting,
              "script": script, "created_at": now,
              "expires_at": now + timedelta(minutes=CLARIFY_MINUTES)}
    stmt = insert(PendingClarification).values(contact_hash=contact_hash, channel=channel,
                                               **values)
    session.execute(stmt.on_conflict_do_update(index_elements=["contact_hash", "channel"],
                                               set_=values))
    session.commit()


def clear_pending(session: Session, contact_hash: str, channel: str) -> None:
    session.execute(delete(PendingClarification).where(
        PendingClarification.contact_hash == contact_hash,
        PendingClarification.channel == channel))
    session.commit()


def purge_expired(session: Session, now: datetime) -> int:
    result = session.execute(delete(PendingClarification)
                             .where(PendingClarification.expires_at <= now))
    session.commit()
    return int(result.rowcount)  # type: ignore[attr-defined]
