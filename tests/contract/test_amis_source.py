"""Contract: AMIS Punjab connector (contracts/price-source.md).

Runs against SYNTHETIC sample pages until real pages are recorded (task T009 after T007).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
import respx

from kisan.prices.sources.amis_punjab import USER_AGENT, AmisPunjabSource

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "sources" / "amis_punjab"
BASE = "https://amis.test"
PAGE = "/daily-prices"
ON = date(2026, 9, 25)


def _page(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class Sleeps:
    def __init__(self) -> None:
        self.calls: list[float] = []

    async def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


@pytest.fixture
def sleeps() -> Sleeps:
    return Sleeps()


def _source(client: httpx.AsyncClient, sleeps: Sleeps) -> AmisPunjabSource:
    return AmisPunjabSource(client, base_url=BASE, page_path=PAGE, sleep=sleeps)


def _mock(router: respx.MockRouter, page: str, robots: str = "robots.txt") -> respx.Route:
    router.get("/robots.txt").mock(return_value=httpx.Response(200, text=_page(robots)))
    return router.get(PAGE).mock(return_value=httpx.Response(200, text=_page(page)))


async def test_normal_day_parsed(sleeps: Sleeps) -> None:
    async with respx.mock(base_url=BASE) as router, httpx.AsyncClient() as client:
        route = _mock(router, "synthetic_normal_day.html")
        result = await _source(client, sleeps).fetch(ON)

    assert result.source_id == "amis_punjab"
    assert result.fetched_at.tzinfo is not None
    rows = {(p.crop_label, p.mandi_label): p for p in result.prices}
    wheat = rows[("Wheat", "Multan")]
    assert wheat.price_date == ON
    assert (wheat.min_price, wheat.max_price) == (Decimal("3900"), Decimal("4050"))
    assert wheat.unit == "40 Kg"
    assert rows[("Maize", "Sahiwal")].min_price == Decimal("62.5")
    # a cell that is not a number becomes None, the row is kept
    okara = rows[("Wheat", "Okara")]
    assert okara.min_price is None and okara.max_price == Decimal("3950")
    # labels are passed through unmapped; mapping happens in normalisation
    assert ("Onion", "Lahore") in rows
    assert result.errors == []
    assert route.calls[0].request.headers["User-Agent"] == USER_AGENT


async def test_missing_crops_day(sleeps: Sleeps) -> None:
    async with respx.mock(base_url=BASE) as router, httpx.AsyncClient() as client:
        _mock(router, "synthetic_missing_crops.html")
        result = await _source(client, sleeps).fetch(ON)
    assert [(p.crop_label, p.mandi_label) for p in result.prices] == [("Wheat", "Multan")]


async def test_layout_change_gives_errors_not_prices(sleeps: Sleeps) -> None:
    async with respx.mock(base_url=BASE) as router, httpx.AsyncClient() as client:
        _mock(router, "synthetic_layout_changed.html")
        result = await _source(client, sleeps).fetch(ON)
    assert result.prices == []
    assert result.errors and "column" in result.errors[0]


async def test_empty_page_gives_no_prices(sleeps: Sleeps) -> None:
    async with respx.mock(base_url=BASE) as router, httpx.AsyncClient() as client:
        _mock(router, "synthetic_empty.html")
        result = await _source(client, sleeps).fetch(ON)
    assert result.prices == []
    assert result.errors


async def test_robots_disallow_means_page_not_requested(sleeps: Sleeps) -> None:
    async with (respx.mock(base_url=BASE, assert_all_called=False) as router,
                httpx.AsyncClient() as client):
        page = _mock(router, "synthetic_normal_day.html", robots="robots_disallow_all.txt")
        result = await _source(client, sleeps).fetch(ON)
    assert page.call_count == 0
    assert result.prices == []
    assert "robots.txt" in result.errors[0]


async def test_waits_between_requests(sleeps: Sleeps) -> None:
    async with respx.mock(base_url=BASE) as router, httpx.AsyncClient() as client:
        _mock(router, "synthetic_normal_day.html")
        await _source(client, sleeps).fetch(ON)
    assert sleeps.calls and min(sleeps.calls) >= 2.0


async def test_retries_twice_then_reports_error(sleeps: Sleeps) -> None:
    async with respx.mock(base_url=BASE) as router, httpx.AsyncClient() as client:
        router.get("/robots.txt").mock(return_value=httpx.Response(200, text=""))
        page = router.get(PAGE).mock(return_value=httpx.Response(503))
        result = await _source(client, sleeps).fetch(ON)
    assert page.call_count == 3
    assert result.prices == []
    assert result.errors


async def test_recovers_after_one_failure(sleeps: Sleeps) -> None:
    async with respx.mock(base_url=BASE) as router, httpx.AsyncClient() as client:
        router.get("/robots.txt").mock(return_value=httpx.Response(200, text=""))
        router.get(PAGE).mock(side_effect=[
            httpx.ConnectError("boom"),
            httpx.Response(200, text=_page("synthetic_missing_crops.html")),
        ])
        result = await _source(client, sleeps).fetch(ON)
    assert len(result.prices) == 1
