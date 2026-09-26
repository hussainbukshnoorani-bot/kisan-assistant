# Contract: Price Source Connector

Every price source is implemented as a connector with this interface. The fetch job calls
`fetch()` and stores the result; nothing else in the system talks to a source directly.

```python
class PriceSource(Protocol):
    id: str                                  # matches PriceSource.id, e.g. "amis_punjab"
    async def fetch(self, on_date: date) -> FetchResult: ...

@dataclass(frozen=True)
class RawPrice:
    crop_label: str       # label exactly as published, e.g. "Wheat" / "گندم"
    mandi_label: str      # label exactly as published
    price_date: date
    min_price: Decimal | None
    max_price: Decimal | None
    unit: str             # as published, e.g. "40kg", "100kg"

@dataclass(frozen=True)
class FetchResult:
    source_id: str
    fetched_at: datetime  # UTC
    prices: list[RawPrice]
    errors: list[str]     # rows that could not be parsed, with reason
```

## Normalisation (fetch job, after `fetch()`)

1. Map `crop_label` / `mandi_label` to IDs through the Synonym table. Unmapped labels are logged
   (`unmapped_label`) and skipped, never guessed.
2. Convert prices to Rs per 40 kg (`per_100kg × 0.4`, `per_kg × 40`, `per_maund` = 40 kg).
   Unknown units: row rejected with `reject_reason = "unknown_unit"`.
3. Validate: at least one of min/max; both > 0; min ≤ max; both within the crop's plausible
   range. Failures are stored with `status = rejected` and a reason (FR-015).
4. Upsert on (source_id, crop_id, mandi_id, price_date).

## Rules for every connector

- MUST respect robots.txt and the source's terms (recorded in `PriceSource.terms_note`).
- MUST send an identifying User-Agent and wait at least 2 s between requests.
- MUST time out each request after 20 s and retry at most twice with backoff.
- MUST be tested against recorded fixtures (`tests/fixtures/sources/<id>/`) including: a normal
  day, a day with missing crops, a layout change (parse returns errors, not wrong prices), and an
  empty page.
- A run that returns 0 valid prices, or fails 3 runs in a row, raises an alert (research R15).
