"""Serverless hosting (Vercel): with inline_replies the reply is sent before the webhook
responds, because the platform may freeze the function once the response is sent."""

from typing import Any

import httpx
import pytest

from tests.helpers import send_sms, send_whatsapp


class ResponseWatcher:
    """ASGI wrapper that records when the response starts."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.started = False

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        async def watch(message: Any) -> None:
            if message["type"] == "http.response.start":
                self.started = True
            await send(message)

        self.started = False
        await self.app(scope, receive, watch)


@pytest.mark.parametrize(("inline", "expected"), [(True, False), (False, True)])
async def test_reply_timing_relative_to_response(settings, engine, whatsapp_api,  # type: ignore[no-untyped-def]
                                                 inline: bool, expected: bool) -> None:
    from kisan.app import create_app

    app = create_app(settings.model_copy(update={"inline_replies": inline}))
    watcher = ResponseWatcher(app)
    seen: list[bool] = []
    original = app.state.services.handler.handle

    async def tracked(message):  # type: ignore[no-untyped-def]
        seen.append(watcher.started)  # had the webhook already responded?
        await original(message)

    app.state.services.handler.handle = tracked
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=watcher),
                                 base_url="http://test") as c:
        await send_whatsapp(c, "923001234567", "salam")
        await send_sms(c, "03001234567", "salam")
    assert seen == [expected, expected]
