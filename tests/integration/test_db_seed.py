"""Migrations and reference seeding against real PostgreSQL."""

from pathlib import Path

import pytest
from sqlalchemy import Engine, inspect, text
from sqlalchemy.exc import IntegrityError

from kisan.jobs.seed_reference import seed_reference

REFERENCE = Path(__file__).resolve().parents[2] / "data" / "reference"

EXPECTED_TABLES = {
    "crops", "mandis", "synonyms", "price_sources", "price_records",
    "pending_clarifications", "conversation_turns",
}


def test_migrations_create_all_tables(engine: Engine) -> None:
    assert EXPECTED_TABLES <= set(inspect(engine).get_table_names())


def test_seed_loads_launch_scope(engine: Engine) -> None:
    with engine.connect() as conn:
        crops = conn.execute(text("SELECT id FROM crops WHERE active ORDER BY id")).scalars().all()
        mandis = conn.execute(text("SELECT count(*) FROM mandis WHERE active")).scalar_one()
        synonyms = conn.execute(text("SELECT count(*) FROM synonyms")).scalar_one()
    assert crops == ["cotton", "maize", "paddy_basmati", "paddy_irri", "wheat"]
    assert mandis == 10
    assert synonyms >= 5 * 5 + 10 * 3


def test_seed_is_idempotent(engine: Engine) -> None:
    with engine.connect() as conn:
        before = conn.execute(text("SELECT count(*) FROM synonyms")).scalar_one()
    seed_reference(engine, REFERENCE)
    with engine.connect() as conn:
        after = conn.execute(text("SELECT count(*) FROM synonyms")).scalar_one()
    assert before == after


def test_crops_removed_from_reference_become_inactive(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO crops (id, name_ur, name_ur_latn, name_en, min_plausible_rs_40kg,"
            " max_plausible_rs_40kg, active) VALUES ('sugarcane', 'x', 'x', 'x', 1, 2, true)"
            " ON CONFLICT (id) DO UPDATE SET active = true"))
    seed_reference(engine, REFERENCE)
    with engine.connect() as conn:
        active = conn.execute(text("SELECT active FROM crops WHERE id = 'sugarcane'")).scalar_one()
    assert active is False


def test_amis_source_disabled_until_terms_verified(engine: Engine) -> None:
    with engine.connect() as conn:
        enabled, verified = conn.execute(text(
            "SELECT enabled, terms_verified_on FROM price_sources WHERE id = 'amis_punjab'"
        )).one()
    assert enabled is False
    assert verified is None


def test_source_cannot_be_enabled_without_terms(engine: Engine) -> None:
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text("UPDATE price_sources SET enabled = true WHERE id = 'amis_punjab'"))


def test_synonym_text_unique_per_entity_type(engine: Engine) -> None:
    with pytest.raises(IntegrityError), engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO synonyms (entity_type, entity_id, script, text_normalized)"
            " VALUES ('crop', 'cotton', 'ur-Latn', 'gandum')"
        ))


def test_neighbours_refer_to_known_mandis(engine: Engine) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT id, neighbours FROM mandis")).all()
    ids = {row.id for row in rows}
    for row in rows:
        assert set(row.neighbours) <= ids - {row.id}, row.id
