"""Lookup outcomes (FR-006, FR-007, FR-008) against the real database."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from kisan.prices.lookup import STALE_LIMIT_DAYS, lookup_outcome
from tests.e2e.prices import add_price

TODAY = date(2026, 9, 26)


@pytest.fixture
def session(engine: Engine):  # type: ignore[no-untyped-def]
    with Session(engine) as s:
        yield s


def test_current_price(engine: Engine, session: Session) -> None:
    rid = add_price(engine, "wheat", "multan", TODAY - timedelta(days=3), 3900, 4050)
    outcome = lookup_outcome(session, "wheat", "multan", TODAY)
    assert outcome.kind == "current"
    assert outcome.price is not None and outcome.price.record_id == rid


def test_newest_wins(engine: Engine, session: Session) -> None:
    add_price(engine, "wheat", "multan", TODAY - timedelta(days=2), 3800, 3900)
    newest = add_price(engine, "wheat", "multan", TODAY - timedelta(days=1), 3900, 4050)
    outcome = lookup_outcome(session, "wheat", "multan", TODAY)
    assert outcome.price is not None and outcome.price.record_id == newest


def test_stale_beyond_three_days_keeps_its_date(engine: Engine, session: Session) -> None:
    add_price(engine, "wheat", "multan", TODAY - timedelta(days=4), 3900, 4050)
    outcome = lookup_outcome(session, "wheat", "multan", TODAY)
    assert outcome.kind == "stale"
    assert outcome.price is not None and outcome.price.price_date == TODAY - timedelta(days=4)


def test_too_old_is_withheld(engine: Engine, session: Session) -> None:
    add_price(engine, "wheat", "multan", TODAY - timedelta(days=STALE_LIMIT_DAYS + 1), 3900,
              4050)
    outcome = lookup_outcome(session, "wheat", "multan", TODAY)
    assert outcome.kind == "none"
    assert outcome.price is None


def test_none(session: Session) -> None:
    assert lookup_outcome(session, "wheat", "multan", TODAY).kind == "none"


def test_neighbouring_mandi_current_price(engine: Engine, session: Session) -> None:
    # Multan's neighbours are [bahawalpur, sahiwal]: the first with a current price is used
    add_price(engine, "wheat", "sahiwal", TODAY - timedelta(days=1), 3950, 4000)
    rid = add_price(engine, "wheat", "bahawalpur", TODAY - timedelta(days=1), 3850, 3950)
    outcome = lookup_outcome(session, "wheat", "multan", TODAY)
    assert outcome.kind == "other_mandi"
    assert outcome.other_mandi_id == "bahawalpur"
    assert outcome.price is not None and outcome.price.record_id == rid


def test_neighbour_preferred_over_stale_requested(engine: Engine, session: Session) -> None:
    add_price(engine, "wheat", "multan", TODAY - timedelta(days=6), 3700, 3800)
    add_price(engine, "wheat", "sahiwal", TODAY - timedelta(days=1), 3950, 4000)
    assert lookup_outcome(session, "wheat", "multan", TODAY).kind == "other_mandi"


def test_stale_neighbour_not_offered(engine: Engine, session: Session) -> None:
    add_price(engine, "wheat", "sahiwal", TODAY - timedelta(days=5), 3950, 4000)
    assert lookup_outcome(session, "wheat", "multan", TODAY).kind == "none"


def test_rejected_and_future_prices_ignored(engine: Engine, session: Session) -> None:
    add_price(engine, "wheat", "multan", TODAY, 0, 0, status="rejected", reject_reason="x")
    add_price(engine, "wheat", "multan", TODAY + timedelta(days=1), 3900, 4000)
    assert lookup_outcome(session, "wheat", "multan", TODAY).kind == "none"
