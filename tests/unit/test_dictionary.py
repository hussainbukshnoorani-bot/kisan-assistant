from pathlib import Path

import pytest

from kisan.understanding.dictionary import Dictionary

REFERENCE = Path(__file__).resolve().parents[2] / "data" / "reference"


@pytest.fixture(scope="module")
def dictionary() -> Dictionary:
    return Dictionary.from_reference(REFERENCE)


@pytest.mark.parametrize(
    ("text", "crops", "mandis"),
    [
        ("Multan mandi mein gandum ka rate kya hai?", ["wheat"], ["multan"]),
        ("ملتان منڈی میں گندم کا ریٹ کیا ہے؟", ["wheat"], ["multan"]),
        ("gehun ka bhao multan", ["wheat"], ["multan"]),
        ("gandam rate Multan", ["wheat"], ["multan"]),
        ("wheat price in multan", ["wheat"], ["multan"]),
        ("Faislabad mandi kapas", ["cotton"], ["faisalabad"]),
        # a general rice/paddy word means both paddy varieties (FR-010)
        ("Rahim Yar Khan mein chawal ka rate", ["paddy_basmati", "paddy_irri"],
         ["rahim_yar_khan"]),
        ("رحیم یار خان چاول", ["paddy_basmati", "paddy_irri"], ["rahim_yar_khan"]),
        ("gujranwala munji", ["paddy_basmati", "paddy_irri"], ["gujranwala"]),
        # a variety word means just that variety
        ("basmati ka rate gujranwala", ["paddy_basmati"], ["gujranwala"]),
        ("Gujranwala IRRI dhaan", ["paddy_irri"], ["gujranwala"]),
        ("گوجرانوالہ باسمتی دھان", ["paddy_basmati"], ["gujranwala"]),
        ("گوجرانوالہ اری", ["paddy_irri"], ["gujranwala"]),
        ("فیصل آباد کپاس", ["cotton"], ["faisalabad"]),
        ("gandum ka rate?", ["wheat"], []),
        ("Lahore mandi ka rate", [], ["lahore"]),
    ],
)
def test_extracts_crops_and_mandis(dictionary: Dictionary, text: str, crops: list[str],
                                   mandis: list[str]) -> None:
    result = dictionary.extract(text)
    assert result.crop_ids == crops
    assert result.mandi_ids == mandis
    assert result.intent == "price"
    assert result.source == "dictionary"


def test_fuzzy_match_on_longer_misspelling(dictionary: Dictionary) -> None:
    assert dictionary.extract("gujranwalla gandum").mandi_ids == ["gujranwala"]


def test_short_words_are_not_fuzzy_matched(dictionary: Dictionary) -> None:
    # "rate" must not fuzzy-match a crop such as "rice"
    result = dictionary.extract("rate kya hai")
    assert result.crop_ids == []
    assert result.mandi_ids == []


def test_several_entities_in_order_capped_at_three(dictionary: Dictionary) -> None:
    result = dictionary.extract("gandum kapas chawal makai multan lahore")
    assert result.crop_ids == ["wheat", "cotton", "paddy_basmati"]
    assert result.mandi_ids == ["multan", "lahore"]


def test_duplicates_collapsed(dictionary: Dictionary) -> None:
    assert dictionary.extract("gandum gehun wheat multan").crop_ids == ["wheat"]


@pytest.mark.parametrize("text", ["mandiyan", "منڈیاں", "fasalain", "list"])
def test_list_intent(dictionary: Dictionary, text: str) -> None:
    assert dictionary.extract(text).intent == "list"


@pytest.mark.parametrize("text", ["salam", "aap kaise hain", "السلام علیکم"])
def test_nothing_found_is_help(dictionary: Dictionary, text: str) -> None:
    result = dictionary.extract(text)
    assert result.intent == "help"
    assert result.crop_ids == [] and result.mandi_ids == []


@pytest.mark.parametrize("text", ["rahim yar khan ganna rate", "رحیم یار خان گنے کا ریٹ",
                                  "sugarcane price"])
def test_sugarcane_is_not_supported(dictionary: Dictionary, text: str) -> None:
    result = dictionary.extract(text)
    assert result.intent == "other"
    assert result.crop_ids == []


def test_supported_crop_wins_over_unsupported_word(dictionary: Dictionary) -> None:
    result = dictionary.extract("ganna nahin, gandum ka rate multan")
    assert result.intent == "price"
    assert result.crop_ids == ["wheat"]


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Wheat", "wheat"),
        ("Seed Cotton(Phutti)", "cotton"),
        ("Paddy Basmati", "paddy_basmati"),
        ("Paddy (IRRI)", "paddy_irri"),
        ("Maize", "maize"),
        ("Rice Basmati Super (New)", None),  # milled rice, not the farmer's paddy
        ("Rice (IRRI)", None),
        ("sugarcane(گنڈ یری)", None),
        ("Onion", None),
    ],
)
def test_source_crop_labels_match_exactly(dictionary: Dictionary, label: str,
                                          expected: str | None) -> None:
    assert dictionary.lookup("crop", label) == expected
