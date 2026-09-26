"""Research R15: collection problems raise alerts (T054)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import Engine, text
from structlog.testing import capture_logs

from kisan.jobs.fetch_prices import run
from kisan.prices.sources import FetchResult, RawPrice
from kisan.understanding.dictionary import Dictionary

DICTIONARY = Dictionary.from_reference(Path(__file__).resolve().parents[2] / "data" /
                                       "reference")


class StubSource:
    id = "fixture"

    def __init__(self, result: FetchResult) -> None:
        self._result = result

    async def fetch(self, on_date: date) -> FetchResult:
        return self._result


def _failed() -> FetchResult:
    return FetchResult("fixture", datetime.now(UTC), [], ["request failed (ConnectError)"])


def _alerts(events: list[dict[str, object]]) -> list[dict[str, object]]:
    return [e for e in events if e["event"] == "fetch_alert"]


async def test_zero_valid_prices_alerts(engine: Engine) -> None:
    only_invalid = FetchResult("fixture", datetime.now(UTC), [
        RawPrice("Wheat", "Multan", date(2026, 9, 25), None, None, "40 Kg")])
    with capture_logs() as events:
        await run(engine, StubSource(only_invalid), DICTIONARY)
    alerts = _alerts(events)
    assert [a["reason"] for a in alerts] == ["no_valid_prices"]
    assert alerts[0]["log_level"] == "error"


async def test_three_consecutive_failures_alert(engine: Engine) -> None:
    with capture_logs() as events:
        for _ in range(3):
            await run(engine, StubSource(_failed()), DICTIONARY)
    reasons = [a["reason"] for a in _alerts(events)]
    assert reasons.count("consecutive_failures") == 1
    assert _alerts(events)[-1]["consecutive_failures"] == 3


async def test_success_resets_failure_count(engine: Engine) -> None:
    good = FetchResult("fixture", datetime.now(UTC), [
        RawPrice("Wheat", "Multan", date(2026, 9, 25), None, None, "40 Kg"),
        RawPrice("Wheat", "Lahore", date(2026, 9, 25), None, 4000, "40 Kg")])
    await run(engine, StubSource(_failed()), DICTIONARY)
    await run(engine, StubSource(_failed()), DICTIONARY)
    await run(engine, StubSource(good), DICTIONARY)
    with engine.connect() as conn:
        count = conn.execute(text(
            "SELECT consecutive_failures FROM price_sources WHERE id = 'fixture'")).scalar_one()
    assert count == 0
