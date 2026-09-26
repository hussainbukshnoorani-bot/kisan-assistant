"""Clarification state (FR-009): 30-minute memory, per channel."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from kisan.conversation.clarification import (
    clear_pending,
    get_pending,
    purge_expired,
    save_pending,
)

NOW = datetime(2026, 9, 26, 7, 0, tzinfo=UTC)
WHO = "hash-1"


@pytest.fixture
def session(engine: Engine):  # type: ignore[no-untyped-def]
    with Session(engine) as s:
        yield s


def test_saved_and_read_back(session: Session) -> None:
    save_pending(session, WHO, "whatsapp", crop_id="wheat", mandi_id=None, awaiting="mandi",
                 script="ur-Latn", now=NOW)
    pending = get_pending(session, WHO, "whatsapp", NOW + timedelta(minutes=29))
    assert pending is not None
    assert (pending.crop_id, pending.mandi_id, pending.awaiting) == ("wheat", None, "mandi")


def test_expires_after_30_minutes(session: Session) -> None:
    save_pending(session, WHO, "whatsapp", crop_id="wheat", mandi_id=None, awaiting="mandi",
                 script="ur-Latn", now=NOW)
    assert get_pending(session, WHO, "whatsapp", NOW + timedelta(minutes=31)) is None


def test_new_question_replaces_pending(session: Session) -> None:
    save_pending(session, WHO, "sms", crop_id="wheat", mandi_id=None, awaiting="mandi",
                 script="ur", now=NOW)
    save_pending(session, WHO, "sms", crop_id=None, mandi_id="multan", awaiting="crop",
                 script="ur", now=NOW + timedelta(minutes=5))
    pending = get_pending(session, WHO, "sms", NOW + timedelta(minutes=6))
    assert pending is not None
    assert (pending.crop_id, pending.mandi_id, pending.awaiting) == (None, "multan", "crop")


def test_separate_per_channel(session: Session) -> None:
    save_pending(session, WHO, "whatsapp", crop_id="wheat", mandi_id=None, awaiting="mandi",
                 script="ur-Latn", now=NOW)
    assert get_pending(session, WHO, "sms", NOW) is None


def test_cleared(session: Session) -> None:
    save_pending(session, WHO, "whatsapp", crop_id="wheat", mandi_id=None, awaiting="mandi",
                 script="ur-Latn", now=NOW)
    clear_pending(session, WHO, "whatsapp")
    assert get_pending(session, WHO, "whatsapp", NOW) is None


def test_purge_removes_only_expired(session: Session) -> None:
    save_pending(session, "old", "whatsapp", crop_id="wheat", mandi_id=None, awaiting="mandi",
                 script="ur-Latn", now=NOW - timedelta(hours=1))
    save_pending(session, "new", "whatsapp", crop_id="wheat", mandi_id=None, awaiting="mandi",
                 script="ur-Latn", now=NOW)
    assert purge_expired(session, NOW) == 1
    assert get_pending(session, "new", "whatsapp", NOW) is not None
