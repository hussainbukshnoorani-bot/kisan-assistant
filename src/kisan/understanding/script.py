"""Script detection (research R10): reply in the script the farmer mostly used."""

from __future__ import annotations

from typing import Literal

Script = Literal["ur", "ur-Latn"]

_ARABIC_RANGES = ((0x0600, 0x06FF), (0x0750, 0x077F), (0xFB50, 0xFDFF), (0xFE70, 0xFEFF))


def _is_arabic(ch: str) -> bool:
    cp = ord(ch)
    return any(lo <= cp <= hi for lo, hi in _ARABIC_RANGES)


def detect_script(text: str) -> Script:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return "ur-Latn"
    arabic = sum(1 for ch in letters if _is_arabic(ch))
    return "ur" if arabic * 2 > len(letters) else "ur-Latn"
