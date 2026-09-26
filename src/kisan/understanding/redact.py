"""Redact CNIC and phone numbers from message text (FR-018, research R12).

Applied before message text is stored, logged, or sent to an AI model.
"""

from __future__ import annotations

import re

from kisan.understanding.normalise import normalise_digits

_SEP = r"[-\s]?"
_CNIC = re.compile(rf"(?<!\d)\d{{5}}{_SEP}\d{{7}}{_SEP}\d(?!\d)")
_PHONE = re.compile(rf"(?<![\d+])(?:\+92|0092|92|0){_SEP}3\d{{2}}{_SEP}\d{{3}}{_SEP}\d{{4}}(?!\d)")


def redact(text: str) -> str:
    text = normalise_digits(text)
    text = _CNIC.sub("[CNIC]", text)
    return _PHONE.sub("[PHONE]", text)
