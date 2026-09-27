"""Fetch, validate, and store prices from one source (research R7).

Usage: python -m kisan.jobs.fetch_prices --source amis_punjab|fixture
Scheduled every 2 hours from 06:00 to 20:00 PKT by the host scheduler.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session

from kisan.db.models import Crop, PriceSource
from kisan.observability import configure_logging, get_logger
from kisan.prices.normalise import CropBounds, normalise_fetch, store
from kisan.prices.sources import FetchResult
from kisan.prices.sources import PriceSource as Connector
from kisan.prices.sources.amis_punjab import AmisPunjabSource
from kisan.prices.sources.fixture import FixtureSource
from kisan.understanding.dictionary import Dictionary

PKT = ZoneInfo("Asia/Karachi")
ALERT_AFTER_FAILURES = 3
log = get_logger(__name__)


def _bounds(engine: Engine) -> dict[str, CropBounds]:
    with engine.connect() as conn:
        rows = conn.execute(select(Crop.id, Crop.min_plausible_rs_40kg,
                                   Crop.max_plausible_rs_40kg)).all()
    return {row.id: CropBounds(row.min_plausible_rs_40kg, row.max_plausible_rs_40kg)
            for row in rows}


def _source_row(engine: Engine, source_id: str) -> PriceSource | None:
    with Session(engine, expire_on_commit=False) as session:
        return session.get(PriceSource, source_id)


@dataclass(frozen=True)
class FetchOutcome:
    result: FetchResult
    valid: int
    rejected: int


async def run(engine: Engine, connector: Connector,
              dictionary: Dictionary) -> FetchOutcome | None:
    """Fetch one source and store its prices. Returns None if the source is disabled."""
    source = _source_row(engine, connector.id)
    if source is None or not source.enabled:
        log.info("fetch_skipped_source_disabled", source_id=connector.id)
        return None
    today = datetime.now(PKT).date()
    result = await connector.fetch(today)
    report = normalise_fetch(result, dictionary, _bounds(engine))
    store(engine, report.rows)
    log.info("fetch_completed", source_id=connector.id, fetched=len(result.prices),
             valid=report.valid, rejected=report.rejected,
             unmapped=sorted(set(report.unmapped_labels)), errors=result.errors)
    _track_failures(engine, connector.id, succeeded=report.valid > 0)
    return FetchOutcome(result, report.valid, report.rejected)


def _track_failures(engine: Engine, source_id: str, succeeded: bool) -> None:
    """A run that stores no valid price is a failure; alert on it, and once more when
    ALERT_AFTER_FAILURES runs in a row have failed (research R15)."""
    with engine.begin() as conn:
        if succeeded:
            conn.execute(update(PriceSource).where(PriceSource.id == source_id)
                         .values(consecutive_failures=0))
            return
        failures = conn.execute(
            update(PriceSource).where(PriceSource.id == source_id)
            .values(consecutive_failures=PriceSource.consecutive_failures + 1)
            .returning(PriceSource.consecutive_failures)).scalar_one()
    log.error("fetch_alert", reason="no_valid_prices", source_id=source_id,
              consecutive_failures=failures)
    if failures == ALERT_AFTER_FAILURES:
        log.error("fetch_alert", reason="consecutive_failures", source_id=source_id,
                  consecutive_failures=failures)


async def _main(source_id: str) -> int:
    from kisan.config import Settings
    from kisan.db import make_engine

    settings = Settings()  # type: ignore[call-arg]
    engine = make_engine(settings.database_url)
    dictionary = Dictionary.from_reference(settings.reference_dir)
    async with httpx.AsyncClient() as client:
        connector: Connector
        if source_id == "fixture":
            connector = FixtureSource(settings.sample_prices_file)
        elif source_id == "amis_punjab":
            source = _source_row(engine, source_id)
            connector = AmisPunjabSource(client, base_url=source.url if source else "")
        else:
            print(f"unknown source {source_id!r}", file=sys.stderr)
            return 2
        await run(engine, connector, dictionary)
    engine.dispose()
    return 0


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, choices=["amis_punjab", "fixture"])
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_main(args.source)))


if __name__ == "__main__":
    main()
