"""Phone number normalisation and hashing (research R12).

Numbers are never stored: only `contact_hash` is persisted or logged.
"""

from __future__ import annotations

import hashlib
import hmac
import re

_SEPARATORS = re.compile(r"[\s\-().]")


def normalise_msisdn(raw: str) -> str:
    """Return the number in E.164 form. Error messages never echo the input."""
    digits = _SEPARATORS.sub("", raw or "")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if digits.startswith("+"):
        body = digits[1:]
    elif digits.startswith("92"):
        body = digits
    elif digits.startswith("0"):
        body = "92" + digits[1:]
    else:
        raise ValueError("invalid phone number")
    if not body.isdigit():
        raise ValueError("invalid phone number")
    if body.startswith("92") and not re.fullmatch(r"92\d{10}", body):
        raise ValueError("invalid phone number")
    if not 8 <= len(body) <= 15:
        raise ValueError("invalid phone number")
    return "+" + body


def contact_hash(pepper: str, channel: str, e164: str) -> str:
    message = f"{channel}:{e164}".encode()
    return hmac.new(pepper.encode(), message, hashlib.sha256).hexdigest()
