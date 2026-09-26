"""WhatsApp Cloud API adapter (research R3, contracts/webhooks.openapi.yaml)."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import httpx

from kisan.channels import InboundMessage, OutboundReply
from kisan.channels.contact import contact_hash, normalise_msisdn


class PayloadError(ValueError):
    pass


def verify_signature(app_secret: str, raw_body: bytes, header: str | None) -> bool:
    if not app_secret or not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def parse_webhook(payload: Any, pepper: str) -> list[InboundMessage]:
    """Extract inbound messages; delivery status updates are ignored."""
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        raise PayloadError("not a WhatsApp webhook")
    messages: list[InboundMessage] = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            for message in (change.get("value") or {}).get("messages") or []:
                messages.append(_to_inbound(message, pepper))
    return messages


def _to_inbound(message: dict[str, Any], pepper: str) -> InboundMessage:
    try:
        e164 = normalise_msisdn("+" + str(message["from"]))
        provider_id = str(message["id"])
        timestamp = int(message["timestamp"])
    except (KeyError, ValueError, TypeError) as exc:
        raise PayloadError("malformed WhatsApp message") from exc
    is_text = message.get("type") == "text"
    return InboundMessage(
        channel="whatsapp",
        contact=e164,
        contact_hash=contact_hash(pepper, "whatsapp", e164),
        provider_message_id=provider_id,
        received_at=datetime.fromtimestamp(timestamp, tz=UTC),
        kind="text" if is_text else "other",
        text=str((message.get("text") or {}).get("body", "")) if is_text else "",
    )


class WhatsAppSender:
    def __init__(self, client: httpx.AsyncClient, api_base: str, phone_number_id: str,
                 access_token: str) -> None:
        self._client = client
        self._url = f"{api_base}/{phone_number_id}/messages"
        self._headers = {"Authorization": f"Bearer {access_token}"}

    async def send(self, reply: OutboundReply) -> None:
        response = await self._client.post(self._url, headers=self._headers, json={
            "messaging_product": "whatsapp",
            "to": reply.contact.removeprefix("+"),
            "type": "text",
            "text": {"body": reply.text},
        })
        response.raise_for_status()
