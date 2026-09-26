"""Price source connector contract (contracts/price-source.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class RawPrice:
    crop_label: str
    mandi_label: str
    price_date: date
    min_price: Decimal | None
    max_price: Decimal | None
    unit: str


@dataclass(frozen=True)
class FetchResult:
    source_id: str
    fetched_at: datetime
    prices: list[RawPrice] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class PriceSource(Protocol):
    id: str

    async def fetch(self, on_date: date) -> FetchResult: ...
