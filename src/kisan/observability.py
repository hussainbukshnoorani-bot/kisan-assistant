"""Structured JSON logging and error capture (constitution Principle VI).

Never pass phone numbers or message text to the logger: log `contact_hash`, IDs, and types.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping
from contextvars import Token
from typing import Any

import structlog
from structlog.contextvars import bind_contextvars, reset_contextvars

_configured = False


def configure_logging(level: int = logging.INFO) -> None:
    global _configured
    if _configured:
        return
    # Logs contain Urdu (e.g. unmapped source labels); a console with a legacy code page must
    # never turn a log line into a crash.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )
    _configured = True


def get_logger(name: str) -> Any:
    return structlog.get_logger(name)


def bind_conversation(conversation_id: str, **values: Any) -> Mapping[str, Token[Any]]:
    return bind_contextvars(conversation_id=conversation_id, **values)


def unbind_conversation(tokens: Mapping[str, Token[Any]]) -> None:
    reset_contextvars(**tokens)


def capture_exception(logger: Any, event: str, exc: BaseException) -> None:
    """Record an unhandled error with its type and traceback, but not its message.

    Exception messages can echo user input, so only the type name is logged as text.
    """
    logger.error(event, error_type=type(exc).__name__,
                 error_location=_location(exc))


def _location(exc: BaseException) -> str:
    tb = exc.__traceback__
    while tb is not None and tb.tb_next is not None:
        tb = tb.tb_next
    if tb is None:
        return "unknown"
    return f"{tb.tb_frame.f_code.co_filename}:{tb.tb_lineno}"
