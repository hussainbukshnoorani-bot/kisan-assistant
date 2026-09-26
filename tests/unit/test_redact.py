import pytest

from kisan.understanding.redact import redact


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("mera CNIC 35202-1234567-1 hai", "mera CNIC [CNIC] hai"),
        ("mera CNIC 3520212345671 hai", "mera CNIC [CNIC] hai"),
        ("number 0300-1234567 pe call karo", "number [PHONE] pe call karo"),
        ("number 0300 123 4567", "number [PHONE]"),
        ("+92 300 1234567", "[PHONE]"),
        ("923001234567", "[PHONE]"),
        ("میرا نمبر ۰۳۰۰۱۲۳۴۵۶۷ ہے", "میرا نمبر [PHONE] ہے"),
        ("شناختی کارڈ ۳۵۲۰۲-۱۲۳۴۵۶۷-۱", "شناختی کارڈ [CNIC]"),
    ],
)
def test_redacts_personal_numbers(raw: str, expected: str) -> None:
    assert redact(raw) == expected


@pytest.mark.parametrize(
    "text",
    [
        "gandum ka rate 3900 se 4050",
        "Rs 3,900 fi 40 kg",
        "26 Sep 2026",
        "Multan mandi mein gandum ka rate kya hai?",
        "1234567",
    ],
)
def test_leaves_ordinary_text_alone(text: str) -> None:
    assert redact(text) == text
