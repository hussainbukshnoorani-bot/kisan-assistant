"""Channel-neutral message types (data-model.md, "In-memory contracts").

`contact` (the E.164 number) lives only in memory for the duration of a reply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, Protocol

ChannelName = Literal["whatsapp", "sms"]
MessageKind = Literal["text", "other"]


@dataclass(frozen=True)
class InboundMessage:
    channel: ChannelName
    contact: str = field(repr=False)
    contact_hash: str
    provider_message_id: str
    received_at: datetime
    kind: MessageKind
    text: str = field(default="", repr=False)


@dataclass(frozen=True)
class OutboundReply:
    channel: ChannelName
    contact: str = field(repr=False)
    text: str
    reply_type: str


class Sender(Protocol):
    async def send(self, reply: OutboundReply) -> None: ...
