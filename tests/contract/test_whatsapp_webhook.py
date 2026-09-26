"""Contract: /webhooks/whatsapp per contracts/webhooks.openapi.yaml."""

import json

import httpx
import respx

from tests.conftest import WA_VERIFY_TOKEN
from tests.helpers import send_whatsapp, wa_payload, wa_signature, whatsapp_replies


async def test_verification_returns_challenge(client: httpx.AsyncClient) -> None:
    r = await client.get("/webhooks/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": WA_VERIFY_TOKEN, "hub.challenge": "12345"})
    assert r.status_code == 200
    assert r.text == "12345"
    assert r.headers["content-type"].startswith("text/plain")


async def test_verification_rejects_wrong_token(client: httpx.AsyncClient) -> None:
    r = await client.get("/webhooks/whatsapp", params={
        "hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"})
    assert r.status_code == 403


async def test_signed_message_accepted_and_answered(client: httpx.AsyncClient,
                                                    whatsapp_api: respx.MockRouter) -> None:
    r = await send_whatsapp(client, "923001234567", "salam")
    assert r.status_code == 200
    replies = whatsapp_replies(whatsapp_api)
    assert len(replies) == 1
    sent = json.loads(whatsapp_api.calls[0].request.content)
    assert sent["to"] == "923001234567"
    assert sent["messaging_product"] == "whatsapp"


async def test_missing_signature_rejected(client: httpx.AsyncClient,
                                          whatsapp_api: respx.MockRouter) -> None:
    body = json.dumps(wa_payload("923001234567", "salam")).encode()
    r = await client.post("/webhooks/whatsapp", content=body,
                          headers={"Content-Type": "application/json"})
    assert r.status_code == 401
    assert whatsapp_api.calls.call_count == 0


async def test_invalid_signature_rejected_without_parsing(client: httpx.AsyncClient) -> None:
    r = await client.post("/webhooks/whatsapp", content=b"not json at all",
                          headers={"X-Hub-Signature-256": "sha256=" + "0" * 64})
    assert r.status_code == 401


async def test_signature_over_different_body_rejected(client: httpx.AsyncClient) -> None:
    body = json.dumps(wa_payload("923001234567", "salam")).encode()
    other = json.dumps(wa_payload("923001234567", "tampered")).encode()
    r = await client.post("/webhooks/whatsapp", content=other,
                          headers={"X-Hub-Signature-256": wa_signature(body)})
    assert r.status_code == 401


async def test_wrong_object_type_is_422(client: httpx.AsyncClient) -> None:
    body = json.dumps({"object": "page", "entry": []}).encode()
    r = await client.post("/webhooks/whatsapp", content=body,
                          headers={"X-Hub-Signature-256": wa_signature(body)})
    assert r.status_code == 422


async def test_status_updates_are_ignored(client: httpx.AsyncClient,
                                          whatsapp_api: respx.MockRouter) -> None:
    payload = wa_payload("923001234567", "x")
    value = payload["entry"][0]["changes"][0]["value"]
    del value["messages"]
    value["statuses"] = [{"id": "wamid.out", "status": "delivered"}]
    body = json.dumps(payload).encode()
    r = await client.post("/webhooks/whatsapp", content=body,
                          headers={"X-Hub-Signature-256": wa_signature(body)})
    assert r.status_code == 200
    assert whatsapp_api.calls.call_count == 0


def test_contract_paths_exist(app) -> None:  # type: ignore[no-untyped-def]
    from pathlib import Path

    import yaml

    spec = yaml.safe_load((Path(__file__).resolve().parents[2] / "specs" /
                           "002-mandi-price-lookup" / "contracts" /
                           "webhooks.openapi.yaml").read_text(encoding="utf-8"))
    routes = {(route.path, method.lower()) for route in app.routes
              for method in getattr(route, "methods", set())}
    for path, operations in spec["paths"].items():
        for method in operations:
            assert (path, method) in routes, (path, method)
