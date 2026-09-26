"""SMS adapter (research R4).

`FakeSmsProvider` is used in development and tests until an aggregator is chosen (task T008);
the vendor adapter (task T076) implements the same `SmsProvider` protocol.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from kisan.channels import InboundMessage, OutboundReply
from kisan.channels.contact import contact_hash, normalise_msisdn
from kisan.observability import get_logger

log = get_logger(__name__)

GSM7_BASIC = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ!\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)
GSM7_EXTENDED = set("^{}\\[~]|€")
SMS_MAX_SEGMENTS = 2


class PayloadError(ValueError):
    pass


def is_gsm7(text: str) -> bool:
    return all(ch in GSM7_BASIC or ch in GSM7_EXTENDED for ch in text)


def sms_length(text: str) -> tuple[int, int]:
    """Return (characters used, character budget for SMS_MAX_SEGMENTS segments)."""
    if is_gsm7(text):
        used = sum(2 if ch in GSM7_EXTENDED else 1 for ch in text)
        return used, 153 * SMS_MAX_SEGMENTS
    return len(text.encode("utf-16-le")) // 2, 67 * SMS_MAX_SEGMENTS


def fits_sms(text: str) -> bool:
    used, budget = sms_length(text)
    return used <= budget


class SmsProvider(Protocol):
    def parse_inbound(self, data: dict[str, Any], pepper: str) -> InboundMessage: ...

    async def send(self, reply: OutboundReply) -> None: ...


class FakeSmsProvider:
    """Accepts the fake inbound schema from the contract and records sent replies."""

    def __init__(self) -> None:
        self.sent: list[OutboundReply] = []

    def parse_inbound(self, data: dict[str, Any], pepper: str) -> InboundMessage:
        try:
            raw_from = str(data["from"])
            provider_id = str(data["message_id"])
            text = str(data["text"])
        except KeyError as exc:
            raise PayloadError("missing field") from exc
        try:
            e164 = normalise_msisdn(raw_from)
        except ValueError as exc:
            raise PayloadError("invalid sender") from exc
        received = data.get("received_at")
        return InboundMessage(
            channel="sms",
            contact=e164,
            contact_hash=contact_hash(pepper, "sms", e164),
            provider_message_id=provider_id,
            received_at=(datetime.fromisoformat(received) if received
                         else datetime.now(UTC)),
            kind="text",
            text=text,
        )

    async def send(self, reply: OutboundReply) -> None:
        self.sent.append(reply)
        log.info("sms_fake_send", reply_type=reply.reply_type, reply=reply.text)
