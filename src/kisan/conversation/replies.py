"""Reply rendering from the reviewed bilingual catalogue (research R9, Principle VIII).

Each catalogue entry is either one template for both channels or a mapping with `whatsapp`
and `sms` variants.
"""

from __future__ import annotations

import string
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal

import yaml

from kisan.channels.sms import fits_sms
from kisan.understanding.script import Script

ChannelName = Literal["whatsapp", "sms"]
SCRIPTS: tuple[Script, ...] = ("ur", "ur-Latn")

CATALOGUE_DIR = Path(__file__).resolve().parent.parent / "catalogue"


class CatalogueError(Exception):
    pass


class Catalogue:
    def __init__(self, entries: dict[str, dict[str, Any]]) -> None:
        self._entries = entries

    @classmethod
    def load(cls, directory: Path = CATALOGUE_DIR) -> Catalogue:
        entries: dict[str, dict[str, Any]] = {}
        for script in SCRIPTS:
            path = directory / f"{script}.yaml"
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not isinstance(data, dict):
                raise CatalogueError(f"{path.name}: expected a mapping")
            entries[script] = data
        if set(entries["ur"]) != set(entries["ur-Latn"]):
            diff = sorted(set(entries["ur"]) ^ set(entries["ur-Latn"]))
            raise CatalogueError(f"catalogue keys differ between scripts: {diff}")
        return cls(entries)

    def keys(self, script: Script) -> set[str]:
        return set(self._entries[script])

    def template(self, key: str, script: Script, channel: ChannelName) -> str:
        try:
            entry = self._entries[script][key]
        except KeyError as exc:
            raise CatalogueError(f"missing catalogue key {key!r} for {script}") from exc
        if isinstance(entry, dict):
            try:
                return str(entry[channel])
            except KeyError as exc:
                raise CatalogueError(f"{key!r} has no {channel} variant") from exc
        return str(entry)

    def render(self, key: str, script: Script, channel: ChannelName, **values: Any) -> str:
        template = self.template(key, script, channel)
        needed = {name for _, name, _, _ in string.Formatter().parse(template) if name}
        missing = needed - values.keys()
        if missing:
            raise CatalogueError(f"{key!r} needs values {sorted(missing)}")
        return template.format(**values).strip()


WHATSAPP_MAX_CHARS = 480


@dataclass(frozen=True)
class PriceLine:
    crop_name: str
    mandi_name: str
    min_rs: int | None
    max_rs: int | None
    source_name: str
    price_date: date


def format_date(catalogue: Catalogue, day: date, script: Script, channel: ChannelName) -> str:
    return f"{day.day} {catalogue.render(f'month_{day.month}', script, channel)}"


def format_price(catalogue: Catalogue, low: int | None, high: int | None, script: Script,
                 channel: ChannelName) -> str:
    values = [v for v in (low, high) if v is not None]
    if not values:
        raise ValueError("price line without a price")
    if len(values) == 1 or low == high:
        return catalogue.render("price_single", script, channel, value=f"{values[-1]:,}")
    return catalogue.render("price_range", script, channel, low=f"{low:,}", high=f"{high:,}")


def render_price_line(catalogue: Catalogue, line: PriceLine, script: Script,
                      channel: ChannelName) -> str:
    return catalogue.render(
        "price", script, channel,
        mandi=line.mandi_name, crop=line.crop_name,
        price=format_price(catalogue, line.min_rs, line.max_rs, script, channel),
        source=line.source_name,
        date=format_date(catalogue, line.price_date, script, channel),
    )


def fits(text: str, channel: ChannelName) -> bool:
    if channel == "sms":
        return fits_sms(text)
    return len(text) <= WHATSAPP_MAX_CHARS


def fit_lines(catalogue: Catalogue, lines: list[str], script: Script,
              channel: ChannelName) -> tuple[str, int]:
    """Join as many lines as fit the channel (at least one), adding a "send the rest" line
    when some are left out (spec edge case, FR-001a)."""
    if fits("\n".join(lines), channel):
        return "\n".join(lines), len(lines)
    more = catalogue.render("more_pairs", script, channel)
    shown = 1
    while shown + 1 < len(lines) and fits("\n".join([*lines[:shown + 1], more]), channel):
        shown += 1
    with_more = "\n".join([*lines[:shown], more])
    return (with_more if fits(with_more, channel) else lines[0]), shown


def render_prices(catalogue: Catalogue, script: Script, channel: ChannelName,
                  lines: list[PriceLine]) -> tuple[str, int]:
    rendered = [render_price_line(catalogue, line, script, channel) for line in lines]
    return fit_lines(catalogue, rendered, script, channel)
