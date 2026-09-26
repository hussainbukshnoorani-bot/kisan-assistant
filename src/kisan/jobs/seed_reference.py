"""Load crops, mandis, synonyms, and price sources from data/reference/ (idempotent).

Usage: python -m kisan.jobs.seed_reference [--dev]
  --dev  also enable the fixture price source (development machines only)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import Engine, delete, update
from sqlalchemy.dialects.postgresql import insert

from kisan.db.models import Crop, Mandi, PriceSource, Synonym
from kisan.understanding.dictionary import Dictionary


def _load(reference_dir: Path, name: str) -> Any:
    return yaml.safe_load((reference_dir / name).read_text(encoding="utf-8"))


def seed_reference(engine: Engine, reference_dir: Path) -> None:
    crops = _load(reference_dir, "crops.yaml")["crops"]
    mandis = _load(reference_dir, "mandis.yaml")["mandis"]
    sources = _load(reference_dir, "sources.yaml")["sources"]
    dictionary = Dictionary.from_reference(reference_dir)

    with engine.begin() as conn:
        for crop in crops:
            stmt = insert(Crop).values(**crop, active=True)
            conn.execute(stmt.on_conflict_do_update(
                index_elements=[Crop.id],
                set_={**{k: stmt.excluded[k] for k in crop if k != "id"}, "active": True}))
        # Crops dropped from the reference data stay in the table (old prices refer to them)
        # but are no longer offered.
        conn.execute(update(Crop).where(Crop.id.not_in([c["id"] for c in crops]))
                     .values(active=False))

        for mandi in mandis:
            stmt = insert(Mandi).values(**mandi, active=True)
            conn.execute(stmt.on_conflict_do_update(
                index_elements=[Mandi.id], set_={k: stmt.excluded[k] for k in mandi if k != "id"}))

        for source in sources:
            stmt = insert(PriceSource).values(**source)
            # Only descriptive fields are refreshed; enabling is done by migration (T079).
            conn.execute(stmt.on_conflict_do_update(
                index_elements=[PriceSource.id],
                set_={k: stmt.excluded[k]
                      for k in ("display_name_ur", "display_name_ur_latn", "url")}))

        conn.execute(delete(Synonym))
        conn.execute(insert(Synonym), [
            {"entity_type": e.entity_type, "entity_id": e.entity_id, "script": e.script,
             "text_normalized": e.text_normalized}
            for e in dictionary.entries()
        ])


def enable_fixture_source(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(update(PriceSource).where(PriceSource.id == "fixture").values(enabled=True))


def main() -> None:
    import argparse

    from kisan.config import Settings
    from kisan.db import make_engine

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args()
    settings = Settings()  # type: ignore[call-arg]
    engine = make_engine(settings.database_url)
    seed_reference(engine, settings.reference_dir)
    if args.dev:
        enable_fixture_source(engine)
    print("reference data loaded" + (" (fixture source enabled)" if args.dev else ""))


if __name__ == "__main__":
    main()
