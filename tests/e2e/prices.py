"""Helpers for putting known prices into the test database."""

from __future__ import annotations

from datetime import date

from sqlalchemy import Engine, text


def add_price(engine: Engine, crop: str, mandi: str, price_date: date, low: int | None,
              high: int | None, *, source: str = "fixture", status: str = "valid",
              reject_reason: str | None = None) -> int:
    with engine.begin() as conn:
        return int(conn.execute(text(
            "INSERT INTO price_records (source_id, crop_id, mandi_id, price_date, min_rs_40kg,"
            " max_rs_40kg, original_unit, fetched_at, status, reject_reason)"
            " VALUES (:source, :crop, :mandi, :d, :low, :high, 'per_40kg', now(), :status,"
            " :reason) RETURNING id"
        ), {"source": source, "crop": crop, "mandi": mandi, "d": price_date, "low": low,
            "high": high, "status": status, "reason": reject_reason}).scalar_one())
