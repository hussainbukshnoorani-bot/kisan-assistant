"""Helpers for building signed webhook requests and reading replies in tests."""

from __future__ import annotations

import hashlib
import hmac
import json
from itertools import count
from typing import Any

import httpx
import respx

from tests.conftest import SMS_SECRET, WA_APP_SECRET

_ids = count(1)


def wa_payload(sender: str, text: str | None, *, msg_id: str | None = None,
               kind: str = "text") -> dict[str, Any]:
    message: dict[str, Any] = {
        "from": sender,
        "id": msg_id or f"wamid.in.{next(_ids)}",
        "timestamp": "1790000000",
        "type": kind,
    }
    if kind == "text":
        message["text"] = {"body": text}
    return {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "waba",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {"phone_number_id": "1234567890"},
                    "messages": [message],
                },
            }],
        }],
    }


def wa_signature(body: bytes, secret: str = WA_APP_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def send_whatsapp(client: httpx.AsyncClient, sender: str, text: str | None, *,
                        msg_id: str | None = None, kind: str = "text") -> httpx.Response:
    body = json.dumps(wa_payload(sender, text, msg_id=msg_id, kind=kind)).encode()
    return await client.post(
        "/webhooks/whatsapp",
        content=body,
        headers={"Content-Type": "application/json", "X-Hub-Signature-256": wa_signature(body)},
    )


async def send_sms(client: httpx.AsyncClient, sender: str, text: str, *,
                   msg_id: str | None = None) -> httpx.Response:
    return await client.post(
        f"/webhooks/sms/{SMS_SECRET}",
        json={"from": sender, "message_id": msg_id or f"sms.{next(_ids)}", "text": text},
    )


def whatsapp_replies(router: respx.MockRouter) -> list[str]:
    return [json.loads(call.request.content)["text"]["body"] for call in router.calls]


def sms_replies(app: Any) -> list[str]:
    return [reply.text for reply in app.state.services.sms.sent]
