"""Find the price to show for a crop at a mandi (FR-004, FR-006)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from kisan.db.models import Mandi, PriceRecord, PriceSource

FRESHNESS_DAYS = 3
# Older prices are withheld rather than shown as stale (FR-006)
STALE_LIMIT_DAYS = 14
PKT = ZoneInfo("Asia/Karachi")


def today_pkt() -> date:
    return datetime.now(PKT).date()


@dataclass(frozen=True)
class FoundPrice:
    record_id: int
    crop_id: str
    mandi_id: str
    price_date: date
    min_rs_40kg: int | None
    max_rs_40kg: int | None
    source_name_ur: str
    source_name_ur_latn: str


@dataclass(frozen=True)
class LookupOutcome:
    kind: Literal["current", "stale", "other_mandi", "none"]
    price: FoundPrice | None = None
    other_mandi_id: str | None = None


def lookup_outcome(session: Session, crop_id: str, mandi_id: str,
                   today: date) -> LookupOutcome:
    """Current price; else a current price at a listed neighbour (FR-008); else the latest
    price up to STALE_LIMIT_DAYS old, labelled stale; else nothing (FR-007)."""
    current = lookup_current(session, crop_id, mandi_id, today)
    if current is not None:
        return LookupOutcome("current", current)
    neighbours = session.scalar(select(Mandi.neighbours).where(Mandi.id == mandi_id)) or []
    for neighbour in neighbours:
        found = lookup_current(session, crop_id, neighbour, today)
        if found is not None:
            return LookupOutcome("other_mandi", found, neighbour)
    stale = _newest(session, crop_id, mandi_id, today,
                    since=today - timedelta(days=STALE_LIMIT_DAYS))
    if stale is not None:
        return LookupOutcome("stale", stale)
    return LookupOutcome("none")


def lookup_current(session: Session, crop_id: str, mandi_id: str,
                   today: date) -> FoundPrice | None:
    """Newest valid price from an enabled source, no older than FRESHNESS_DAYS."""
    return _newest(session, crop_id, mandi_id, today,
                   since=today - timedelta(days=FRESHNESS_DAYS))


def _newest(session: Session, crop_id: str, mandi_id: str, today: date,
            since: date | None) -> FoundPrice | None:
    query = (
        select(PriceRecord, PriceSource)
        .join(PriceSource, PriceSource.id == PriceRecord.source_id)
        .where(PriceRecord.crop_id == crop_id, PriceRecord.mandi_id == mandi_id,
               PriceRecord.status == "valid", PriceSource.enabled.is_(True),
               PriceRecord.price_date <= today)
        .order_by(PriceRecord.price_date.desc(), PriceRecord.fetched_at.desc())
        .limit(1)
    )
    if since is not None:
        query = query.where(PriceRecord.price_date >= since)
    row = session.execute(query).first()
    if row is None:
        return None
    record, source = row
    return FoundPrice(record.id, record.crop_id, record.mandi_id, record.price_date,
                      record.min_rs_40kg, record.max_rs_40kg, source.display_name_ur,
                      source.display_name_ur_latn)
