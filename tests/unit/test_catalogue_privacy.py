"""FR-014 / Principle IV: no reply template asks farmers for personal data."""

import re

from kisan.conversation.replies import Catalogue

FORBIDDEN = [
    r"\bcnic\b", r"shanakhti", r"شناختی", r"\bpin\b", r"\botp\b", r"password", r"پاس ورڈ",
    r"account", r"اکاؤنٹ", r"khata", r"کھاتہ", r"card number", r"کارڈ نمبر",
]


def test_no_template_requests_personal_data() -> None:
    catalogue = Catalogue.load()
    for script in ("ur", "ur-Latn"):
        for key in catalogue.keys(script):  # type: ignore[arg-type]
            for channel in ("whatsapp", "sms"):
                text = catalogue.template(key, script, channel).lower()  # type: ignore[arg-type]
                for pattern in FORBIDDEN:
                    assert not re.search(pattern, text), (script, key, pattern)
