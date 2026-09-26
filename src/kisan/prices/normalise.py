"""Turn fetched prices into stored PriceRecords (contracts/price-source.md, "Normalisation")."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import Engine
from sqlalchemy.dialects.postgresql import insert

from kisan.db.models import PriceRecord
from kisan.prices.sources import FetchResult, RawPrice
from kisan.understanding.dictionary import Dictionary

_UNITS: list[tuple[str, str, Decimal]] = [
    (r"^(per)?(40kg|maund|mound|mann|man)$", "per_40kg", Decimal(1)),
    (r"^(per)?100kg$", "per_100kg", Decimal("0.4")),
    (r"^(per)?1?kg$", "per_kg", Decimal(40)),
]


class UnknownUnitError(ValueError):
    pass


def unit_factor(unit: str) -> tuple[str, Decimal]:
    key = re.sub(r"[\s.]", "", unit.lower())
    for pattern, name, factor in _UNITS:
        if re.fullmatch(pattern, key):
            return name, factor
    raise UnknownUnitError("unknown unit")


def to_rs_per_40kg(value: Decimal | None, unit: str) -> int | None:
    _, factor = unit_factor(unit)
    if value is None:
        return None
    return int((value * factor).quantize(Decimal(1), rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class CropBounds:
    min_rs_40kg: int
    max_rs_40kg: int


@dataclass
class NormaliseReport:
    rows: list[dict[str, Any]]
    unmapped_labels: list[str]

    @property
    def valid(self) -> int:
        return sum(1 for r in self.rows if r["status"] == "valid")

    @property
    def rejected(self) -> int:
        return sum(1 for r in self.rows if r["status"] == "rejected")


def normalise_fetch(result: FetchResult, dictionary: Dictionary,
                    bounds: dict[str, CropBounds]) -> NormaliseReport:
    rows: list[dict[str, Any]] = []
    unmapped: list[str] = []
    seen: set[tuple[str, str, Any]] = set()
    for raw in result.prices:
        crop_id = dictionary.lookup("crop", raw.crop_label)
        mandi_id = dictionary.lookup("mandi", raw.mandi_label)
        if crop_id is None or mandi_id is None:
            unmapped.append(raw.crop_label if crop_id is None else raw.mandi_label)
            continue
        key = (crop_id, mandi_id, raw.price_date)
        if key in seen:
            continue
        seen.add(key)
        rows.append(_row(result.source_id, result.fetched_at, crop_id, mandi_id, raw,
                         bounds.get(crop_id)))
    return NormaliseReport(rows, unmapped)


def _row(source_id: str, fetched_at: datetime, crop_id: str, mandi_id: str, raw: RawPrice,
         bounds: CropBounds | None) -> dict[str, Any]:
    row: dict[str, Any] = {
        "source_id": source_id, "crop_id": crop_id, "mandi_id": mandi_id,
        "price_date": raw.price_date, "fetched_at": fetched_at,
        "original_unit": raw.unit or "unknown", "min_rs_40kg": None, "max_rs_40kg": None,
        "status": "valid", "reject_reason": None,
    }
    try:
        row["original_unit"] = unit_factor(raw.unit)[0]
        row["min_rs_40kg"] = to_rs_per_40kg(raw.min_price, raw.unit)
        row["max_rs_40kg"] = to_rs_per_40kg(raw.max_price, raw.unit)
    except UnknownUnitError:
        return {**row, "status": "rejected", "reject_reason": "unknown_unit"}
    reason = validate(row["min_rs_40kg"], row["max_rs_40kg"], bounds)
    if reason:
        return {**row, "status": "rejected", "reject_reason": reason}
    return row


def validate(low: int | None, high: int | None, bounds: CropBounds | None) -> str | None:
    """Return a rejection reason, or None if the price may be shown (FR-015)."""
    values = [v for v in (low, high) if v is not None]
    if not values:
        return "no_price"
    if any(v <= 0 for v in values):
        return "not_positive"
    if low is not None and high is not None and low > high:
        return "min_above_max"
    if bounds is not None and any(
            not bounds.min_rs_40kg <= v <= bounds.max_rs_40kg for v in values):
        return "out_of_range"
    return None


def store(engine: Engine, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    stmt = insert(PriceRecord).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["source_id", "crop_id", "mandi_id", "price_date"],
        set_={col: stmt.excluded[col] for col in (
            "min_rs_40kg", "max_rs_40kg", "original_unit", "fetched_at", "status",
            "reject_reason")},
    )
    with engine.begin() as conn:
        conn.execute(stmt)
