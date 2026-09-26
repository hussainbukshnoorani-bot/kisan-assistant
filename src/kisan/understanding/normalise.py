"""Text normalisation for Urdu script and Roman Urdu (research R8).

Used for both farmer messages and dictionary synonyms, so matching compares like with like.
"""

from __future__ import annotations

import re
import unicodedata

_DIGITS = {
    **{chr(0x06F0 + d): str(d) for d in range(10)},  # Urdu/Persian digits
    **{chr(0x0660 + d): str(d) for d in range(10)},  # Arabic-Indic digits
}
_DIGIT_MAP = str.maketrans(_DIGITS)
_CHAR_MAP = str.maketrans({
    "ي": "ی",  # Arabic yeh → Farsi/Urdu yeh
    "ى": "ی",  # alef maksura → yeh
    "ك": "ک",  # Arabic kaf → keheh
    "ه": "ہ",  # Arabic heh → heh goal
    "ۀ": "ہ",  # heh with yeh above → heh goal
    **_DIGITS,
})

_REMOVE = re.compile("[ـً-ٰٟ]")  # tatweel and diacritics
_PUNCT = re.compile(r"[^\w\s]|_", flags=re.UNICODE)
_SPACE = re.compile(r"\s+")


def normalise_digits(text: str) -> str:
    return text.translate(_DIGIT_MAP)


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_CHAR_MAP)
    text = _REMOVE.sub("", text)
    text = _PUNCT.sub(" ", text.lower())
    return _SPACE.sub(" ", text).strip()
