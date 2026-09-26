"""Contract: /webhooks/sms/{secret} per contracts/webhooks.openapi.yaml (fake provider)."""

import httpx

from tests.conftest import SMS_SECRET
from tests.helpers import sms_replies


async def test_json_message_accepted(client: httpx.AsyncClient, app) -> None:  # type: ignore[no-untyped-def]
    r = await client.post(f"/webhooks/sms/{SMS_SECRET}",
                          json={"from": "03001234567", "message_id": "m1", "text": "salam"})
    assert r.status_code == 200
    assert len(sms_replies(app)) == 1
    assert app.state.services.sms.sent[0].contact == "+923001234567"


async def test_form_message_accepted(client: httpx.AsyncClient, app) -> None:  # type: ignore[no-untyped-def]
    r = await client.post(f"/webhooks/sms/{SMS_SECRET}",
                          data={"from": "+923001234567", "message_id": "m2", "text": "salam"})
    assert r.status_code == 200
    assert len(sms_replies(app)) == 1


async def test_wrong_secret_rejected(client: httpx.AsyncClient, app) -> None:  # type: ignore[no-untyped-def]
    r = await client.post("/webhooks/sms/" + "x" * 40,
                          json={"from": "03001234567", "message_id": "m3", "text": "salam"})
    assert r.status_code == 401
    assert sms_replies(app) == []


async def test_missing_fields_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post(f"/webhooks/sms/{SMS_SECRET}", json={"from": "03001234567"})
    assert r.status_code == 422


async def test_invalid_number_rejected(client: httpx.AsyncClient) -> None:
    r = await client.post(f"/webhooks/sms/{SMS_SECRET}",
                          json={"from": "abc", "message_id": "m4", "text": "salam"})
    assert r.status_code == 422
