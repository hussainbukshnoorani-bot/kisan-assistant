"""FastAPI application: webhooks and health check (contracts/webhooks.openapi.yaml).

Run with: uvicorn kisan.app:create_app --factory
"""

from __future__ import annotations

import hmac
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

import httpx
from fastapi import BackgroundTasks, FastAPI, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import Engine, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from kisan.channels import InboundMessage, sms, whatsapp
from kisan.channels.sms import FakeSmsProvider, SmsProvider
from kisan.channels.whatsapp import WhatsAppSender
from kisan.config import Settings
from kisan.conversation.handler import Handler
from kisan.conversation.replies import Catalogue
from kisan.db import make_engine, make_session_factory
from kisan.db.models import PriceRecord
from kisan.observability import configure_logging, get_logger
from kisan.prices.lookup import FRESHNESS_DAYS, today_pkt
from kisan.understanding.dictionary import Dictionary

log = get_logger(__name__)


@dataclass
class Services:
    settings: Settings
    engine: Engine
    sessions: sessionmaker[Session]
    http: httpx.AsyncClient
    whatsapp: WhatsAppSender
    sms: SmsProvider
    handler: Handler


def build_services(settings: Settings) -> Services:
    engine = make_engine(settings.database_url)
    sessions = make_session_factory(engine)
    http = httpx.AsyncClient(timeout=httpx.Timeout(5.0))
    wa_sender = WhatsAppSender(http, settings.whatsapp_api_base,
                               settings.whatsapp_phone_number_id,
                               settings.whatsapp_access_token.get_secret_value())
    sms_provider = FakeSmsProvider()
    handler = Handler(
        sessions=sessions,
        catalogue=Catalogue.load(),
        dictionary=Dictionary.from_reference(settings.reference_dir),
        senders={"whatsapp": wa_sender, "sms": sms_provider},
    )
    return Services(settings, engine, sessions, http, wa_sender, sms_provider, handler)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()  # type: ignore[call-arg]
    configure_logging()
    services = build_services(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        await services.http.aclose()
        services.engine.dispose()

    app = FastAPI(title="Kisan Assistant", lifespan=lifespan)
    app.state.services = services

    async def _dispatch(message: InboundMessage, background: BackgroundTasks) -> None:
        # The handler is looked up at call time so tests can wrap it.
        if settings.inline_replies:
            await services.handler.handle(message)
        else:
            background.add_task(services.handler.handle, message)

    @app.get("/webhooks/whatsapp", response_class=PlainTextResponse)
    async def whatsapp_verify(
        mode: str = Query(alias="hub.mode"),
        verify_token: str = Query(alias="hub.verify_token"),
        challenge: str = Query(alias="hub.challenge"),
    ) -> PlainTextResponse:
        expected = settings.whatsapp_verify_token.get_secret_value()
        if mode == "subscribe" and expected and hmac.compare_digest(verify_token, expected):
            return PlainTextResponse(challenge)
        return PlainTextResponse("forbidden", status_code=403)

    @app.post("/webhooks/whatsapp")
    async def whatsapp_inbound(request: Request, background: BackgroundTasks) -> JSONResponse:
        raw = await request.body()
        if not whatsapp.verify_signature(settings.whatsapp_app_secret.get_secret_value(), raw,
                                         request.headers.get("X-Hub-Signature-256")):
            log.warning("whatsapp_signature_invalid")
            return JSONResponse({"error": "invalid signature"}, status_code=401)
        try:
            messages = whatsapp.parse_webhook(json.loads(raw), _pepper(settings))
        except (ValueError, whatsapp.PayloadError):
            return JSONResponse({"error": "not a WhatsApp message webhook"}, status_code=422)
        for message in messages:
            await _dispatch(message, background)
        return JSONResponse({"status": "accepted"})

    @app.post("/webhooks/sms/{secret}")
    async def sms_inbound(secret: str, request: Request,
                          background: BackgroundTasks) -> JSONResponse:
        if not hmac.compare_digest(secret, settings.sms_webhook_secret.get_secret_value()):
            log.warning("sms_secret_invalid")
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            data = await _read_body(request)
            message = services.sms.parse_inbound(data, _pepper(settings))
        except (ValueError, sms.PayloadError):
            return JSONResponse({"error": "invalid SMS payload"}, status_code=422)
        await _dispatch(message, background)
        return JSONResponse({"status": "accepted"})

    @app.get("/health")
    async def health() -> JSONResponse:
        try:
            with services.sessions() as session:
                newest = session.scalar(
                    select(func.max(PriceRecord.price_date)).where(PriceRecord.status == "valid"))
        except SQLAlchemyError:
            log.error("health_database_down")
            return JSONResponse({"status": "down", "database": "down",
                                 "newest_price_date": None}, status_code=503)
        fresh = newest is not None and today_pkt() - newest <= timedelta(days=FRESHNESS_DAYS)
        return JSONResponse({
            "status": "ok" if fresh else "degraded",
            "database": "ok",
            "newest_price_date": newest.isoformat() if newest else None,
        })

    return app


def _pepper(settings: Settings) -> str:
    return settings.contact_hash_pepper.get_secret_value()


async def _read_body(request: Request) -> dict[str, Any]:
    if request.headers.get("content-type", "").startswith("application/json"):
        data = await request.json()
        if not isinstance(data, dict):
            raise ValueError("expected an object")
        return data
    form = await request.form()
    return {key: value for key, value in form.items() if isinstance(value, str)}
