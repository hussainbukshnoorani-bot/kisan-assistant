"""Daily scheduled job: refresh prices from every enabled source, then purge old data.

Triggered by Vercel Cron via GET /jobs/daily (vercel.json `crons`), or run directly with
`python -m kisan.jobs.daily`. Disabled sources are skipped, so AMIS stays off until T079.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import Engine

from kisan.config import Settings
from kisan.jobs.fetch_prices import _source_row, run
from kisan.jobs.purge import purge
from kisan.prices.sources import PriceSource as Connector
from kisan.prices.sources.amis_punjab import AmisPunjabSource
from kisan.prices.sources.fixture import FixtureSource
from kisan.understanding.dictionary import Dictionary


async def run_daily(engine: Engine, settings: Settings, client: httpx.AsyncClient,
                    dictionary: Dictionary) -> dict[str, Any]:
    amis_row = _source_row(engine, "amis_punjab")
    connectors: list[Connector] = [
        FixtureSource(settings.sample_prices_file),
        AmisPunjabSource(client, base_url=amis_row.url if amis_row else ""),
    ]
    sources: dict[str, Any] = {}
    for connector in connectors:
        outcome = await run(engine, connector, dictionary)
        if outcome is None:
            sources[connector.id] = "skipped (disabled)"
            continue
        sources[connector.id] = {"fetched": len(outcome.result.prices), "valid": outcome.valid,
                                 "rejected": outcome.rejected, "errors": outcome.result.errors}
    purged = purge(engine, datetime.now(UTC))
    return {"sources": sources, "purged": asdict(purged)}


async def _main() -> None:
    import json

    from kisan.db import make_engine
    from kisan.observability import configure_logging

    configure_logging()
    settings = Settings()  # type: ignore[call-arg]
    engine = make_engine(settings.database_url)
    async with httpx.AsyncClient() as client:
        summary = await run_daily(engine, settings, client,
                                  Dictionary.from_reference(settings.reference_dir))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())
