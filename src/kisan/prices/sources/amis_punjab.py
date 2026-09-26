"""AMIS Punjab connector (research R6).

The page layout is not yet confirmed: parsing is driven by column headers and has only been
tested against SYNTHETIC sample pages. Record real pages and update `_COLUMNS` / `page_path`
after task T007 confirms retrieval is permitted. The source stays disabled until then.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from urllib.robotparser import RobotFileParser

import httpx
from selectolax.parser import HTMLParser, Node

from kisan.prices.sources import FetchResult, RawPrice

USER_AGENT = "KisanAssistantBot/0.1 (farmer price information; contact via project owner)"
MIN_INTERVAL_S = 2.0
TIMEOUT_S = 20.0
RETRIES = 2

# header text (lowercase, contains) → field; the first matching field wins
_COLUMNS: list[tuple[str, tuple[str, ...]]] = [
    ("crop", ("commodity", "crop")),
    ("mandi", ("city", "market", "mandi")),
    ("date", ("date",)),
    ("min", ("min",)),
    ("max", ("max",)),
    ("unit", ("unit",)),
]
_REQUIRED = {"crop", "mandi", "date"}
_DATE_FORMATS = ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%b-%Y")

Sleep = Callable[[float], Awaitable[None]]


class AmisPunjabSource:
    id = "amis_punjab"

    def __init__(self, client: httpx.AsyncClient, base_url: str, page_path: str = "/",
                 sleep: Sleep = asyncio.sleep) -> None:
        self._client = client
        self._base = base_url.rstrip("/")
        self._path = page_path
        self._sleep = sleep
        self._made_request = False

    async def fetch(self, on_date: date) -> FetchResult:
        fetched_at = datetime.now(UTC)
        errors: list[str] = []
        page_url = self._base + self._path

        robots = await self._robots()
        if robots is not None and not robots.can_fetch(USER_AGENT, page_url):
            return FetchResult(self.id, fetched_at, [], ["page disallowed by robots.txt"])

        html = await self._get(page_url, errors)
        if html is None:
            return FetchResult(self.id, fetched_at, [], errors)
        prices, parse_errors = parse_page(html)
        return FetchResult(self.id, fetched_at, prices, errors + parse_errors)

    async def _robots(self) -> RobotFileParser | None:
        # An unreachable robots.txt is treated as "no restrictions".
        text = await self._get(self._base + "/robots.txt", [], retries=0)
        if text is None:
            return None
        parser = RobotFileParser()
        parser.parse(text.splitlines())
        return parser

    async def _get(self, url: str, errors: list[str], retries: int = RETRIES) -> str | None:
        for attempt in range(retries + 1):
            await self._wait_turn(backoff=attempt)
            try:
                response = await self._client.get(url, headers={"User-Agent": USER_AGENT},
                                                  timeout=TIMEOUT_S)
                if response.status_code == 404 and url.endswith("/robots.txt"):
                    return ""
                response.raise_for_status()
                return response.text
            except httpx.HTTPError as exc:
                errors.append(f"request failed ({type(exc).__name__}), attempt {attempt + 1}")
        return None

    async def _wait_turn(self, backoff: int) -> None:
        """Wait at least MIN_INTERVAL_S before every request after the first, longer on retry."""
        if self._made_request:
            await self._sleep(MIN_INTERVAL_S * (2 ** backoff))
        self._made_request = True


def parse_page(html: str) -> tuple[list[RawPrice], list[str]]:
    tree = HTMLParser(html)
    tables = tree.css("table")
    if not tables:
        return [], ["no price table found"]
    prices: list[RawPrice] = []
    errors: list[str] = []
    for table in tables:
        rows = table.css("tr")
        if not rows:
            continue
        columns = _map_columns(rows[0])
        if not _REQUIRED <= columns.keys() or not ({"min", "max"} & columns.keys()):
            errors.append(f"unexpected column layout: {_cell_texts(rows[0])}")
            continue
        for index, row in enumerate(rows[1:], start=2):
            cells = _cell_texts(row)
            if len(cells) <= max(columns.values()):
                errors.append(f"row {index}: too few cells")
                continue
            try:
                prices.append(RawPrice(
                    crop_label=cells[columns["crop"]],
                    mandi_label=cells[columns["mandi"]],
                    price_date=_parse_date(cells[columns["date"]]),
                    min_price=_number(cells[columns["min"]]) if "min" in columns else None,
                    max_price=_number(cells[columns["max"]]) if "max" in columns else None,
                    unit=cells[columns["unit"]] if "unit" in columns else "",
                ))
            except ValueError as exc:
                errors.append(f"row {index}: {exc}")
    return prices, errors


def _cell_texts(row: Node) -> list[str]:
    return [(cell.text() or "").strip() for cell in row.css("th, td")]


def _map_columns(header: Node) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for position, title in enumerate(_cell_texts(header)):
        lowered = title.lower()
        for field_name, needles in _COLUMNS:
            if field_name not in mapping and any(n in lowered for n in needles):
                mapping[field_name] = position
                break
    return mapping


def _parse_date(text: str) -> date:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError("unrecognised date")


def _number(text: str) -> Decimal | None:
    cleaned = re.sub(r"[,\s]", "", text)
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None
