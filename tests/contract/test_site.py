"""Public business website: home, privacy policy, terms (for Meta business verification and
the WhatsApp app's privacy-policy URL)."""

from __future__ import annotations

import httpx
import pytest


@pytest.mark.parametrize("path", ["/", "/privacy", "/terms"])
async def test_pages_are_public_html(client: httpx.AsyncClient, path: str) -> None:
    r = await client.get(path)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Kisan Assistant" in r.text
    assert 'href="/privacy"' in r.text and 'href="/terms"' in r.text


async def test_home_explains_the_service(client: httpx.AsyncClient) -> None:
    text = (await client.get("/")).text
    assert "mandi" in text.lower()
    assert "WhatsApp" in text and "SMS" in text


async def test_privacy_policy_matches_what_the_app_does(client: httpx.AsyncClient) -> None:
    text = (await client.get("/privacy")).text
    for fact in ("90 days", "[CNIC]", "phone number", "WhatsApp", "delete"):
        assert fact in text, fact


async def test_missing_business_details_are_marked_not_invented(client: httpx.AsyncClient) -> None:
    text = (await client.get("/")).text
    assert "To be added" in text


async def test_meta_domain_verification_tag(settings, engine, whatsapp_api) -> None:  # type: ignore[no-untyped-def]
    from kisan.app import create_app

    app = create_app(settings.model_copy(update={"meta_domain_verification": "abc123xyz"}))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                 base_url="http://test") as c:
        text = (await c.get("/")).text
    assert '<meta name="facebook-domain-verification" content="abc123xyz">' in text


async def test_business_details_are_html_escaped(client: httpx.AsyncClient, app) -> None:  # type: ignore[no-untyped-def]
    from kisan.site import render_page

    html = render_page("home", {"legal_name": "<script>x</script>"}, None)
    assert "<script>x</script>" not in html
