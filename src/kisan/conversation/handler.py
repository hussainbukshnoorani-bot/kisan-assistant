"""Conversation orchestration: one inbound message → one reply (research R11)."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from kisan.channels import ChannelName, InboundMessage, OutboundReply, Sender
from kisan.conversation.clarification import clear_pending, get_pending, save_pending
from kisan.conversation.replies import (
    Catalogue,
    PriceLine,
    fit_lines,
    fits,
    format_date,
    format_price,
    render_price_line,
)
from kisan.db.models import ConversationTurn, Crop, Mandi
from kisan.observability import (
    bind_conversation,
    capture_exception,
    get_logger,
    unbind_conversation,
)
from kisan.prices.lookup import FoundPrice, LookupOutcome, lookup_outcome, today_pkt
from kisan.understanding.dictionary import Dictionary, ExtractionResult
from kisan.understanding.redact import redact
from kisan.understanding.script import Script, detect_script

log = get_logger(__name__)

MAX_PAIRS = 3
# When several pairs are answered, the reply type reflects the most useful line.
_LINE_PRIORITY = ["price", "price_other_mandi", "price_stale", "no_price"]


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass
class Decision:
    reply_type: str
    text: str
    crop_ids: list[str] = field(default_factory=list)
    mandi_ids: list[str] = field(default_factory=list)
    price_record_ids: list[int] = field(default_factory=list)
    understood_by: str = "none"


class Handler:
    def __init__(self, sessions: sessionmaker[Session], catalogue: Catalogue,
                 dictionary: Dictionary, senders: Mapping[ChannelName, Sender],
                 clock: Callable[[], datetime] = utcnow) -> None:
        self._sessions = sessions
        self._catalogue = catalogue
        self._dictionary = dictionary
        self._senders = senders
        self._clock = clock
        # FR-013: "checking" message after holding_after s; give up at give_up_after s.
        self.holding_after = 5.0
        self.give_up_after = 9.0

    async def handle(self, message: InboundMessage) -> None:
        turn_id = uuid.uuid4()
        tokens = bind_conversation(str(turn_id), channel=message.channel,
                                   contact_hash=message.contact_hash)
        started = time.monotonic()
        try:
            script: Script = detect_script(message.text) if message.text.strip() else "ur-Latn"
            try:
                script = await asyncio.to_thread(self._script_for, message)
                if not await asyncio.to_thread(self._record_turn, turn_id, message, script):
                    log.info("duplicate_message_ignored")
                    return
            except SQLAlchemyError as exc:
                # The farmer still gets an answer when the database is down (US2 scenario 4).
                log.error("database_unavailable", error_type=type(exc).__name__)
                await self._send(message, self._catalogue.render(
                    "source_down", script, message.channel), "source_down")
                return
            decision, holding = await self._decide_in_time(message, script)
            await self._send(message, decision.text, decision.reply_type)
            latency_ms = int((time.monotonic() - started) * 1000)
            await asyncio.to_thread(self._complete_turn, turn_id, decision, latency_ms, holding)
            log.info("reply_sent", reply_type=decision.reply_type, script=script,
                     understood_by=decision.understood_by, holding_message_sent=holding,
                     price_record_ids=decision.price_record_ids, latency_ms=latency_ms)
        except Exception as exc:  # noqa: BLE001 - background task: log and stop
            capture_exception(log, "handle_message_failed", exc)
        finally:
            unbind_conversation(tokens)

    async def _decide_in_time(self, message: InboundMessage,
                              script: Script) -> tuple[Decision, bool]:
        task = asyncio.ensure_future(asyncio.to_thread(self._decide, message, script))
        holding = False
        try:
            done, _ = await asyncio.wait({task}, timeout=self.holding_after)
            if not done:
                holding = True
                await self._send(message, self._catalogue.render(
                    "checking", script, message.channel), "checking")
                await asyncio.wait_for(asyncio.shield(task),
                                       timeout=self.give_up_after - self.holding_after)
            return task.result(), holding
        except (TimeoutError, SQLAlchemyError) as exc:
            log.warning("answer_unavailable", error_type=type(exc).__name__)
            return Decision("source_down", self._catalogue.render(
                "source_down", script, message.channel)), holding

    async def _send(self, message: InboundMessage, text: str, reply_type: str) -> None:
        await self._senders[message.channel].send(OutboundReply(
            channel=message.channel, contact=message.contact, text=text,
            reply_type=reply_type))

    # -- steps (run in a worker thread; they use the synchronous DB session) --

    def _script_for(self, message: InboundMessage) -> Script:
        if message.kind == "text" and message.text.strip():
            return detect_script(message.text)
        with self._sessions() as session:
            last = session.scalars(
                select(ConversationTurn.script)
                .where(ConversationTurn.contact_hash == message.contact_hash,
                       ConversationTurn.channel == message.channel)
                .order_by(ConversationTurn.received_at.desc()).limit(1)
            ).first()
        return "ur" if last == "ur" else "ur-Latn"

    def _record_turn(self, turn_id: uuid.UUID, message: InboundMessage, script: Script) -> bool:
        """Insert the turn before replying; a repeated delivery conflicts (FR-019)."""
        with self._sessions() as session:
            session.add(ConversationTurn(
                id=turn_id,
                provider_message_id=message.provider_message_id,
                contact_hash=message.contact_hash,
                channel=message.channel,
                received_at=message.received_at,
                message_text=redact(message.text) if message.text else None,
                script=script,
            ))
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False
        return True

    def _decide(self, message: InboundMessage, script: Script) -> Decision:
        channel = message.channel
        if message.kind != "text" or not message.text.strip():
            return Decision("non_text", self._catalogue.render("non_text", script, channel))
        result = self._dictionary.extract(message.text)
        with self._sessions() as session:
            if result.intent == "price":
                return self._price_or_question(session, message, result, script)
            if result.intent == "list":
                return Decision("list", self._list_text(session, result.list_kind or "both",
                                                        script, channel),
                                understood_by=result.source)
        if result.intent == "other":
            return Decision("unsupported", self._catalogue.render("unsupported", script, channel),
                            understood_by=result.source)
        return Decision("help", self._catalogue.render("help", script, channel))

    def _price_or_question(self, session: Session, message: InboundMessage,
                           result: ExtractionResult, script: Script) -> Decision:
        """Answer, or ask one question for the missing crop or mandi (FR-009, US3)."""
        channel = message.channel
        pending = get_pending(session, message.contact_hash, channel, self._clock())
        crops = result.crop_ids or ([pending.crop_id] if pending and pending.crop_id else [])
        mandis = result.mandi_ids or ([pending.mandi_id] if pending and pending.mandi_id else [])
        if crops and mandis:
            if pending is not None:
                clear_pending(session, message.contact_hash, channel)
            understood = replace(result, crop_ids=crops, mandi_ids=mandis)
            return self._price_decision(session, understood, script, channel)
        if crops:
            save_pending(session, message.contact_hash, channel, crop_id=crops[0],
                         mandi_id=None, awaiting="mandi", script=script, now=self._clock())
            crop = _names(session, Crop, script)[crops[0]]
            return Decision("ask_mandi", self._catalogue.render("ask_mandi", script, channel,
                                                                crop=crop),
                            crop_ids=crops, understood_by=result.source)
        save_pending(session, message.contact_hash, channel, crop_id=None, mandi_id=mandis[0],
                     awaiting="crop", script=script, now=self._clock())
        mandi = _names(session, Mandi, script)[mandis[0]]
        return Decision("ask_crop", self._catalogue.render("ask_crop", script, channel,
                                                           mandi=mandi),
                        mandi_ids=mandis, understood_by=result.source)

    def _list_text(self, session: Session, kind: str, script: Script,
                   channel: ChannelName) -> str:
        """Supported mandis and/or crops (FR-011). If both do not fit the channel, the mandis
        are listed with a hint for asking about crops."""
        separator = self._catalogue.template("list_separator", script, channel)

        def names(model: type[Crop] | type[Mandi]) -> str:
            rows = session.execute(select(model.name_ur, model.name_ur_latn)
                                   .where(model.active).order_by(model.name_ur_latn)).all()
            return separator.join(ur if script == "ur" else latn for ur, latn in rows)

        crops = self._catalogue.render("list_crops", script, channel, crops=names(Crop))
        if kind == "crops":
            return crops
        mandis = self._catalogue.render("list_mandis", script, channel, mandis=names(Mandi))
        if kind == "mandis":
            return mandis
        hint = self._catalogue.render("list_crops_hint", script, channel)
        for text in ("\n".join([mandis, crops]), "\n".join([mandis, hint])):
            if fits(text, channel):
                return text
        return mandis

    def _price_decision(self, session: Session, result: ExtractionResult, script: Script,
                        channel: ChannelName) -> Decision:
        crop_names = _names(session, Crop, script)
        mandi_names = _names(session, Mandi, script)
        today = today_pkt()
        pairs = [(c, m) for c in result.crop_ids for m in result.mandi_ids][:MAX_PAIRS]
        lines: list[str] = []
        kinds: list[str] = []
        line_ids: list[int | None] = []
        for crop_id, mandi_id in pairs:
            outcome = lookup_outcome(session, crop_id, mandi_id, today)
            kind, text = self._line(outcome, crop_names[crop_id], mandi_names, mandi_id,
                                    script, channel)
            lines.append(text)
            kinds.append(kind)
            line_ids.append(outcome.price.record_id if outcome.price else None)
        text, shown = fit_lines(self._catalogue, lines, script, channel)
        reply_type = min(kinds[:shown], key=_LINE_PRIORITY.index)
        return Decision(reply_type, text, crop_ids=result.crop_ids, mandi_ids=result.mandi_ids,
                        price_record_ids=[i for i in line_ids[:shown] if i is not None],
                        understood_by=result.source)

    def _line(self, outcome: LookupOutcome, crop: str, mandi_names: dict[str, str],
              mandi_id: str, script: Script, channel: ChannelName) -> tuple[str, str]:
        mandi = mandi_names[mandi_id]
        found = outcome.price
        if outcome.kind == "none" or found is None:
            return "no_price", self._catalogue.render("no_price", script, channel,
                                                      mandi=mandi, crop=crop)
        if outcome.kind == "current":
            return "price", render_price_line(self._catalogue, PriceLine(
                crop, mandi, found.min_rs_40kg, found.max_rs_40kg,
                _source_name(found, script), found.price_date), script, channel)
        values = {
            "mandi": mandi, "crop": crop, "source": _source_name(found, script),
            "price": format_price(self._catalogue, found.min_rs_40kg, found.max_rs_40kg,
                                  script, channel),
            "date": format_date(self._catalogue, found.price_date, script, channel),
        }
        if outcome.kind == "other_mandi" and outcome.other_mandi_id:
            return "price_other_mandi", self._catalogue.render(
                "price_other_mandi", script, channel,
                other_mandi=mandi_names[outcome.other_mandi_id], **values)
        return "price_stale", self._catalogue.render("price_stale", script, channel, **values)

    def _complete_turn(self, turn_id: uuid.UUID, decision: Decision, latency_ms: int,
                       holding: bool) -> None:
        with self._sessions() as session:
            turn = session.get_one(ConversationTurn, turn_id)
            turn.reply_type = decision.reply_type
            turn.understood_by = decision.understood_by
            turn.crop_ids = decision.crop_ids
            turn.mandi_ids = decision.mandi_ids
            turn.price_record_ids = decision.price_record_ids
            turn.replied_at = self._clock()
            turn.latency_ms = latency_ms
            turn.holding_message_sent = holding
            session.commit()


def _names(session: Session, model: type[Crop] | type[Mandi], script: Script) -> dict[str, str]:
    rows = session.execute(select(model.id, model.name_ur, model.name_ur_latn)).all()
    return {row.id: (row.name_ur if script == "ur" else row.name_ur_latn) for row in rows}


def _source_name(found: FoundPrice, script: Script) -> str:
    return found.source_name_ur if script == "ur" else found.source_name_ur_latn
