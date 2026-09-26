import pytest

from kisan.channels.contact import contact_hash, normalise_msisdn

PEPPER = "pepper-0123456789abcdef"


@pytest.mark.parametrize(
    "raw",
    ["03001234567", "0300-1234567", "0300 123 4567", "+923001234567", "923001234567",
     "00923001234567"],
)
def test_normalise_pakistani_numbers(raw: str) -> None:
    assert normalise_msisdn(raw) == "+923001234567"


def test_keeps_other_e164_numbers() -> None:
    assert normalise_msisdn("+447700900123") == "+447700900123"


@pytest.mark.parametrize("raw", ["", "abc", "12", "+92abc"])
def test_rejects_invalid(raw: str) -> None:
    with pytest.raises(ValueError, match="invalid phone number"):
        normalise_msisdn(raw)


def test_invalid_number_error_does_not_echo_the_input() -> None:
    with pytest.raises(ValueError) as exc:
        normalise_msisdn("0300-12345")
    assert "12345" not in str(exc.value)


def test_hash_is_stable_and_channel_specific() -> None:
    a = contact_hash(PEPPER, "whatsapp", "+923001234567")
    assert a == contact_hash(PEPPER, "whatsapp", "+923001234567")
    assert a != contact_hash(PEPPER, "sms", "+923001234567")
    assert a != contact_hash("other-pepper-0123456789", "whatsapp", "+923001234567")


def test_hash_does_not_contain_number() -> None:
    h = contact_hash(PEPPER, "sms", "+923001234567")
    assert "3001234567" not in h
    assert len(h) == 64
