"""Price reply rendering: required fields (FR-005), lengths (FR-012, FR-001a)."""

from datetime import date

import pytest

from kisan.channels.sms import fits_sms, is_gsm7, sms_length
from kisan.conversation.replies import Catalogue, PriceLine, format_date, render_prices

CAT = Catalogue.load()
DAY = date(2026, 9, 26)

LONG_LATN = PriceLine(crop_name="Chawal", mandi_name="Rahim Yar Khan", min_rs=10000,
                      max_rs=12500, source_name="AMIS Punjab", price_date=DAY)
LONG_UR = PriceLine(crop_name="مکئی", mandi_name="رحیم یار خان", min_rs=10000, max_rs=12500,
                    source_name="اے ایم آئی ایس پنجاب", price_date=DAY)


def test_range_in_roman_urdu() -> None:
    line = PriceLine("Gandum", "Multan", 3900, 4050, "AMIS Punjab", date(2026, 9, 25))
    text, shown = render_prices(CAT, "ur-Latn", "whatsapp", [line])
    assert shown == 1
    assert "Multan" in text and "Gandum" in text
    assert "Rs 3,900-4,050" in text
    assert "40 kg" in text
    assert "AMIS Punjab" in text
    assert "25 Sep" in text


def test_single_price_when_min_equals_max_or_missing() -> None:
    for low, high in ((4000, 4000), (None, 4000), (4000, None)):
        line = PriceLine("Gandum", "Multan", low, high, "AMIS Punjab", DAY)
        text, _ = render_prices(CAT, "ur-Latn", "sms", [line])
        assert "Rs 4,000 " in text
        assert "-" not in text.split("Rs ")[1].split(" ")[0]


def test_urdu_script_fields() -> None:
    line = PriceLine("گندم", "ملتان", 3900, 4050, "اے ایم آئی ایس پنجاب", date(2026, 9, 25))
    text, _ = render_prices(CAT, "ur", "whatsapp", [line])
    for part in ("ملتان", "گندم", "3,900", "4,050", "40 کلو", "اے ایم آئی ایس پنجاب", "25 ستمبر"):
        assert part in text


@pytest.mark.parametrize(("month", "latn", "ur"), [(1, "Jan", "جنوری"), (12, "Dec", "دسمبر")])
def test_date_format(month: int, latn: str, ur: str) -> None:
    assert format_date(CAT, date(2026, month, 3), "ur-Latn", "sms") == f"3 {latn}"
    assert format_date(CAT, date(2026, month, 3), "ur", "sms") == f"3 {ur}"


def test_whatsapp_three_pairs_within_480() -> None:
    for script, line in (("ur-Latn", LONG_LATN), ("ur", LONG_UR)):
        text, shown = render_prices(CAT, script, "whatsapp", [line, line, line])
        assert shown == 3
        assert len(text) <= 480, (script, len(text))


def test_roman_urdu_sms_uses_gsm7_and_fits() -> None:
    text, shown = render_prices(CAT, "ur-Latn", "sms", [LONG_LATN])
    assert shown == 1
    assert is_gsm7(text), [ch for ch in text if not is_gsm7(ch)]
    assert fits_sms(text)


def test_urdu_sms_single_pair_fits_unicode_budget() -> None:
    text, shown = render_prices(CAT, "ur", "sms", [LONG_UR])
    assert shown == 1
    used, budget = sms_length(text)
    assert budget == 134
    assert used <= budget


def test_roman_urdu_sms_fits_three_pairs() -> None:
    text, shown = render_prices(CAT, "ur-Latn", "sms", [LONG_LATN] * 3)
    assert shown == 3
    assert fits_sms(text)


def test_urdu_sms_multi_pair_trimmed_with_send_rest_line() -> None:
    text, shown = render_prices(CAT, "ur", "sms", [LONG_UR] * 3)
    assert 1 <= shown < 3
    assert fits_sms(text)
    assert CAT.render("more_pairs", "ur", "sms") in text


def test_whatsapp_never_adds_send_rest_line_when_all_fit() -> None:
    text, shown = render_prices(CAT, "ur-Latn", "whatsapp", [LONG_LATN])
    assert shown == 1
    assert CAT.render("more_pairs", "ur-Latn", "whatsapp") not in text


def test_every_roman_urdu_sms_template_is_gsm7() -> None:
    for key in CAT.keys("ur-Latn"):
        assert is_gsm7(CAT.template(key, "ur-Latn", "sms")), key


@pytest.mark.parametrize("script", ["ur", "ur-Latn"])
@pytest.mark.parametrize("key", ["no_price", "price_stale", "price_other_mandi"])
def test_every_single_line_fits_sms_with_longest_values(script: str, key: str) -> None:
    long = LONG_UR if script == "ur" else LONG_LATN
    values = {
        "mandi": long.mandi_name, "crop": long.crop_name, "other_mandi": long.mandi_name,
        "source": long.source_name, "date": format_date(CAT, date(2026, 9, 30), script, "sms"),  # type: ignore[arg-type]
        "price": CAT.render("price_range", script, "sms", low="10,000", high="12,500"),  # type: ignore[arg-type]
    }
    text = CAT.render(key, script, "sms", **values)  # type: ignore[arg-type]
    assert fits_sms(text), (key, script, sms_length(text))
