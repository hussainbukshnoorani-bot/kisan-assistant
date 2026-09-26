import pytest

from kisan.understanding.script import detect_script


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ملتان منڈی میں گندم کا ریٹ کیا ہے؟", "ur"),
        ("Multan mandi mein gandum ka rate kya hai?", "ur-Latn"),
        ("wheat price in Multan", "ur-Latn"),  # English is answered in Roman Urdu
        ("Multan منڈی میں گندم کا ریٹ", "ur"),  # mostly Urdu script
        ("ملتان mandi mein gandum ka rate kya hai", "ur-Latn"),  # mostly Latin
        ("123 ???", "ur-Latn"),  # no letters
        ("", "ur-Latn"),
    ],
)
def test_detect_script(text: str, expected: str) -> None:
    assert detect_script(text) == expected
