"""Development price source that reads illustrative prices from a YAML file."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import yaml

from kisan.prices.sources import FetchResult, RawPrice

DEFAULT_FILE = Path("data/sample_prices.yaml")


class FixtureSource:
    id = "fixture"

    def __init__(self, path: Path = DEFAULT_FILE) -> None:
        self._path = path

    async def fetch(self, on_date: date) -> FetchResult:
        data = yaml.safe_load(self._path.read_text(encoding="utf-8"))
        prices = [
            RawPrice(
                crop_label=str(row["crop"]),
                mandi_label=str(row["mandi"]),
                price_date=on_date - timedelta(days=int(row["days_ago"])),
                min_price=_decimal(row.get("min")),
                max_price=_decimal(row.get("max")),
                unit=str(row["unit"]),
            )
            for row in data["prices"]
        ]
        return FetchResult(self.id, datetime.now(UTC), prices, [])


def _decimal(value: object) -> Decimal | None:
    return None if value is None else Decimal(str(value))
