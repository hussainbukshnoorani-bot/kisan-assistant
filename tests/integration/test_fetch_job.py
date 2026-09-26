"""Fetch job end to end against the fixture source (T046)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import Engine, text

from kisan.jobs.fetch_prices import run
from kisan.prices.sources.fixture import FixtureSource
from kisan.understanding.dictionary import Dictionary

ROOT = Path(__file__).resolve().parents[2]
DICTIONARY = Dictionary.from_reference(ROOT / "data" / "reference")
FIXTURE = ROOT / "tests" / "fixtures" / "sources" / "fixture" / "prices.yaml"


def _prices(engine: Engine) -> dict[tuple[str, str], tuple[int | None, int | None, str]]:
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT crop_id, mandi_id, min_rs_40kg, max_rs_40kg, status FROM price_records"
        )).all()
    return {(r.crop_id, r.mandi_id): (r.min_rs_40kg, r.max_rs_40kg, r.status) for r in rows}


async def test_fixture_prices_stored_and_converted(engine: Engine) -> None:
    result = await run(engine, FixtureSource(FIXTURE), DICTIONARY)
    assert result is not None
    prices = _prices(engine)
    assert prices[("wheat", "multan")] == (3900, 4050, "valid")
    assert prices[("paddy_basmati", "gujranwala")] == (3800, 4400, "valid")  # per 100 kg × 0.4
    assert prices[("paddy_irri", "gujranwala")] == (1400, 1500, "valid")
    assert ("sugarcane", "rahim_yar_khan") not in prices
    assert prices[("maize", "sahiwal")] == (2500, 2600, "valid")  # per kg × 40


async def test_rerun_updates_instead_of_duplicating(engine: Engine) -> None:
    await run(engine, FixtureSource(FIXTURE), DICTIONARY)
    await run(engine, FixtureSource(FIXTURE), DICTIONARY)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT count(*) FROM price_records")).scalar_one()
    assert count == 8


async def test_disabled_source_is_skipped(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("UPDATE price_sources SET enabled = false WHERE id = 'fixture'"))
    try:
        assert await run(engine, FixtureSource(FIXTURE), DICTIONARY) is None
        assert _prices(engine) == {}
    finally:
        with engine.begin() as conn:
            conn.execute(text("UPDATE price_sources SET enabled = true WHERE id = 'fixture'"))


def test_source_labels_map_exactly() -> None:
    assert DICTIONARY.lookup("crop", "Paddy Basmati") == "paddy_basmati"
    assert DICTIONARY.lookup("crop", "Onion") is None
    assert DICTIONARY.lookup("mandi", "Rahim Yar Khan") == "rahim_yar_khan"
    assert DICTIONARY.lookup("mandi", "Multan Cantt") == "multan"
    assert DICTIONARY.lookup("crop", "Multan") is None
