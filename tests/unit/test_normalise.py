import pytest

from kisan.understanding.normalise import normalise


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Multan Mandi mein GANDUM ka rate?", "multan mandi mein gandum ka rate"),
        ("  gandum,   kapas!! ", "gandum kapas"),
        # Arabic yeh / kaf → Urdu forms
        ("كپاس", "کپاس"),
        ("گندمي", "گندمی"),
        ("ى", "ی"),
        # Arabic heh → Urdu heh goal
        ("گوجرانواله", "گوجرانوالہ"),
        # tatweel and diacritics removed
        ("گنــدم", "گندم"),
        ("گنّا", "گنا"),
        # Urdu punctuation becomes spaces
        ("ملتان منڈی میں گندم کا ریٹ کیا ہے؟", "ملتان منڈی میں گندم کا ریٹ کیا ہے"),
        ("گندم، کپاس۔", "گندم کپاس"),
        # Urdu and Arabic-Indic digits → ASCII
        ("۴۰ کلو", "40 کلو"),
        ("٤٠", "40"),
    ],
)
def test_normalise(raw: str, expected: str) -> None:
    assert normalise(raw) == expected


def test_normalise_is_idempotent() -> None:
    once = normalise("Multan منڈی، گنـدم كا ريٹ؟")
    assert normalise(once) == once
