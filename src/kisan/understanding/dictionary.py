"""Deterministic crop / mandi extraction with a normalising synonym dictionary (research R8)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml
from rapidfuzz import fuzz, process

from kisan.understanding.normalise import normalise

EntityType = Literal["crop", "mandi"]
Intent = Literal["price", "list", "help", "other"]
ListKind = Literal["mandis", "crops", "both"]
Match = tuple[tuple[EntityType, str], ...]

FUZZY_SCORE_CUTOFF = 88
FUZZY_MIN_LENGTH = 4
MAX_ENTITIES = 3


@dataclass(frozen=True)
class ExtractionResult:
    crop_ids: list[str] = field(default_factory=list)
    mandi_ids: list[str] = field(default_factory=list)
    intent: Intent = "help"
    source: Literal["dictionary", "llm"] = "dictionary"
    list_kind: ListKind | None = None


@dataclass(frozen=True)
class SynonymEntry:
    entity_type: EntityType
    entity_id: str
    script: str
    text_normalized: str


@dataclass(frozen=True)
class Vocabulary:
    """Word lists from synonyms.yaml other than the per-entity spellings."""

    list_words: dict[str, ListKind] = field(default_factory=dict)
    stopwords: set[str] = field(default_factory=set)
    price_words: set[str] = field(default_factory=set)
    unsupported_words: set[str] = field(default_factory=set)
    crop_groups: dict[str, list[str]] = field(default_factory=dict)  # word → crop ids
    source_crop_labels: dict[str, str] = field(default_factory=dict)  # label → crop id


class Dictionary:
    def __init__(self, entries: list[SynonymEntry], vocabulary: Vocabulary) -> None:
        self._entries = entries
        self._vocab = vocabulary
        self._exact: dict[str, Match] = {
            e.text_normalized: ((e.entity_type, e.entity_id),) for e in entries
        }
        for word, crop_ids in vocabulary.crop_groups.items():
            self._exact.setdefault(word, tuple(("crop", c) for c in crop_ids))
        self._max_words = max((len(text.split()) for text in self._exact), default=1)
        self._fuzzy_keys = [
            text for text in self._exact
            if text.isascii() and " " not in text and len(text) >= FUZZY_MIN_LENGTH
        ]

    @classmethod
    def from_reference(cls, reference_dir: Path) -> Dictionary:
        data = yaml.safe_load((reference_dir / "synonyms.yaml").read_text(encoding="utf-8"))
        entries: list[SynonymEntry] = []
        seen: set[tuple[str, str]] = set()
        for entity_type, section in (("crop", "crops"), ("mandi", "mandis")):
            for entity_id, scripts in data[section].items():
                for script, words in scripts.items():
                    for word in words:
                        text = normalise(str(word))
                        if (entity_type, text) in seen:
                            continue
                        seen.add((entity_type, text))
                        entries.append(SynonymEntry(entity_type, entity_id, script, text))  # type: ignore[arg-type]
        return cls(entries, _vocabulary(data))

    def entries(self) -> Iterator[SynonymEntry]:
        return iter(self._entries)

    def lookup(self, entity_type: EntityType, label: str) -> str | None:
        """Map a price-source label to an ID; never guesses.

        Crop labels must equal one of the reviewed `source_labels`. A mandi label may contain
        extra words ("Multan Cantt"); it maps only if every matched phrase is the same mandi.
        """
        if entity_type == "crop":
            return self._vocab.source_crop_labels.get(normalise(label))
        tokens = normalise(label).split()
        found: set[str] = set()
        i = 0
        while i < len(tokens):
            for width in range(min(self._max_words, len(tokens) - i), 0, -1):
                match = self._exact.get(" ".join(tokens[i:i + width]))
                if match is not None:
                    found.update(eid for etype, eid in match if etype == entity_type)
                    i += width
                    break
            else:
                i += 1
        return found.pop() if len(found) == 1 else None

    def extract(self, text: str) -> ExtractionResult:
        tokens = normalise(text).split()
        crops: list[str] = []
        mandis: list[str] = []
        list_kind: ListKind | None = None
        asks_price = False
        names_unsupported = False

        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in self._vocab.unsupported_words:
                names_unsupported = True
                i += 1
                continue
            match, width = self._match_at(tokens, i)
            if match is not None:
                for entity_type, entity_id in match:
                    target = crops if entity_type == "crop" else mandis
                    if entity_id not in target and len(target) < MAX_ENTITIES:
                        target.append(entity_id)
                i += width
                continue
            if token in self._vocab.list_words:
                list_kind = list_kind or self._vocab.list_words[token]
            elif token in self._vocab.price_words:
                asks_price = True
            i += 1

        if crops or (mandis and not names_unsupported):
            intent: Intent = "price"
        elif names_unsupported:
            intent = "other"  # names a crop we do not cover
        elif list_kind:
            intent = "list"
        elif asks_price:
            intent = "other"  # a price question about something we do not cover
        else:
            intent = "help"
        if intent == "other":
            crops, mandis = [], []
        return ExtractionResult(crop_ids=crops, mandi_ids=mandis, intent=intent,
                                list_kind=list_kind if intent == "list" else None)

    def _match_at(self, tokens: list[str], i: int) -> tuple[Match | None, int]:
        for width in range(min(self._max_words, len(tokens) - i), 0, -1):
            phrase = " ".join(tokens[i:i + width])
            if phrase in self._exact:
                return self._exact[phrase], width
        token = tokens[i]
        if (token.isascii() and len(token) >= FUZZY_MIN_LENGTH
                and token not in self._vocab.stopwords and token not in self._vocab.list_words):
            best = process.extractOne(token, self._fuzzy_keys, scorer=fuzz.ratio,
                                      score_cutoff=FUZZY_SCORE_CUTOFF)
            if best is not None:
                return self._exact[best[0]], 1
        return None, 1


def _words(values: Any) -> set[str]:
    return {normalise(str(w)) for w in values or []}


def _vocabulary(data: dict[str, Any]) -> Vocabulary:
    groups: dict[str, list[str]] = {}
    for group in (data.get("crop_groups") or {}).values():
        for word in _words(group["words"]):
            groups[word] = list(group["crops"])
    labels = {normalise(str(label)): crop_id
              for crop_id, crop_labels in (data.get("source_labels") or {}).get("crops", {}).items()
              for label in crop_labels}
    return Vocabulary(
        list_words={normalise(str(w)): kind
                    for kind, words in data["list_words"].items() for w in words},
        stopwords=_words(data["stopwords"]),
        price_words={w for words in (data.get("price_words") or {}).values()
                     for w in _words(words)},
        unsupported_words=_words(data.get("unsupported_crops")),
        crop_groups=groups,
        source_crop_labels=labels,
    )
