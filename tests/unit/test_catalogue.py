import string
from pathlib import Path

import pytest

from kisan.conversation.replies import Catalogue, CatalogueError

CATALOGUE_DIR = Path(__file__).resolve().parents[2] / "src" / "kisan" / "catalogue"


@pytest.fixture(scope="module")
def catalogue() -> Catalogue:
    return Catalogue.load(CATALOGUE_DIR)


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_both_scripts_have_the_same_keys(catalogue: Catalogue) -> None:
    assert catalogue.keys("ur") == catalogue.keys("ur-Latn")


def test_placeholders_match_between_scripts(catalogue: Catalogue) -> None:
    for key in catalogue.keys("ur"):
        for channel in ("whatsapp", "sms"):
            ur = catalogue.template(key, "ur", channel)
            latn = catalogue.template(key, "ur-Latn", channel)
            assert _fields(ur) == _fields(latn), key


def test_render_substitutes_values(catalogue: Catalogue) -> None:
    text = catalogue.render("help", "ur-Latn", "whatsapp")
    assert "gandum" in text.lower()


def test_missing_key_raises(catalogue: Catalogue) -> None:
    with pytest.raises(CatalogueError):
        catalogue.render("does_not_exist", "ur", "sms")


def test_missing_value_raises(tmp_path: Path) -> None:
    for name in ("ur", "ur-Latn"):
        (tmp_path / f"{name}.yaml").write_text("greet: 'hi {name}'\n", encoding="utf-8")
    with pytest.raises(CatalogueError):
        Catalogue.load(tmp_path).render("greet", "ur", "sms")


def test_mismatched_catalogues_rejected(tmp_path: Path) -> None:
    (tmp_path / "ur.yaml").write_text("a: x\n", encoding="utf-8")
    (tmp_path / "ur-Latn.yaml").write_text("b: y\n", encoding="utf-8")
    with pytest.raises(CatalogueError):
        Catalogue.load(tmp_path)
