"""SQLAlchemy models (specs/002-mandi-price-lookup/data-model.md).

No table stores a phone number: conversations are keyed by `contact_hash` (research R12).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Crop(Base):
    __tablename__ = "crops"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name_ur: Mapped[str] = mapped_column(Text)
    name_ur_latn: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)
    min_plausible_rs_40kg: Mapped[int] = mapped_column(Integer)
    max_plausible_rs_40kg: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        CheckConstraint(
            "min_plausible_rs_40kg > 0 AND max_plausible_rs_40kg > min_plausible_rs_40kg",
            name="plausible_range",
        ),
    )


class Mandi(Base):
    __tablename__ = "mandis"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name_ur: Mapped[str] = mapped_column(Text)
    name_ur_latn: Mapped[str] = mapped_column(Text)
    name_en: Mapped[str] = mapped_column(Text)
    district: Mapped[str] = mapped_column(Text)
    province: Mapped[str] = mapped_column(Text)
    neighbours: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Synonym(Base):
    __tablename__ = "synonyms"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(10))
    entity_id: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(String(10))
    text_normalized: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("entity_type", "text_normalized"),
        CheckConstraint("entity_type IN ('crop', 'mandi')", name="entity_type"),
        CheckConstraint("script IN ('ur', 'ur-Latn', 'en')", name="script"),
    )


class PriceSource(Base):
    __tablename__ = "price_sources"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name_ur: Mapped[str] = mapped_column(Text)
    display_name_ur_latn: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    terms_note: Mapped[str | None] = mapped_column(Text)
    terms_verified_on: Mapped[date | None] = mapped_column(Date)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    __table_args__ = (
        CheckConstraint(
            "NOT enabled OR (terms_note IS NOT NULL AND terms_note <> ''"
            " AND terms_verified_on IS NOT NULL)",
            name="terms_before_enable",
        ),
    )


class PriceRecord(Base):
    __tablename__ = "price_records"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("price_sources.id"))
    crop_id: Mapped[str] = mapped_column(ForeignKey("crops.id"))
    mandi_id: Mapped[str] = mapped_column(ForeignKey("mandis.id"))
    price_date: Mapped[date] = mapped_column(Date)
    min_rs_40kg: Mapped[int | None] = mapped_column(Integer)
    max_rs_40kg: Mapped[int | None] = mapped_column(Integer)
    original_unit: Mapped[str] = mapped_column(Text)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(10))
    reject_reason: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("source_id", "crop_id", "mandi_id", "price_date"),
        Index("ix_price_records_lookup", "crop_id", "mandi_id", "price_date"),
        CheckConstraint("status IN ('valid', 'rejected')", name="status"),
        CheckConstraint("status = 'valid' OR reject_reason IS NOT NULL", name="reject_reason"),
        CheckConstraint(
            "status = 'rejected' OR ((min_rs_40kg IS NOT NULL OR max_rs_40kg IS NOT NULL)"
            " AND (min_rs_40kg IS NULL OR max_rs_40kg IS NULL OR min_rs_40kg <= max_rs_40kg))",
            name="valid_values",
        ),
    )


class PendingClarification(Base):
    __tablename__ = "pending_clarifications"

    contact_hash: Mapped[str] = mapped_column(Text, primary_key=True)
    channel: Mapped[str] = mapped_column(String(10), primary_key=True)
    crop_id: Mapped[str | None] = mapped_column(Text)
    mandi_id: Mapped[str | None] = mapped_column(Text)
    awaiting: Mapped[str] = mapped_column(String(10))
    script: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("channel IN ('whatsapp', 'sms')", name="channel"),
        CheckConstraint("awaiting IN ('crop', 'mandi')", name="awaiting"),
    )


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    provider_message_id: Mapped[str] = mapped_column(Text)
    contact_hash: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(10))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    message_text: Mapped[str | None] = mapped_column(Text)
    script: Mapped[str] = mapped_column(String(10))
    understood_by: Mapped[str] = mapped_column(String(12), default="none")
    crop_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    mandi_ids: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    reply_type: Mapped[str | None] = mapped_column(String(24))
    price_record_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), default=list)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    holding_message_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint("channel", "provider_message_id"),
        Index("ix_conversation_turns_received_at", "received_at"),
        CheckConstraint("channel IN ('whatsapp', 'sms')", name="channel"),
    )
