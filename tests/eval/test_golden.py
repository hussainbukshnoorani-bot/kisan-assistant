"""Golden eval set (constitution Principle II, SC-001, SC-002).

Each case in golden.yaml is run through message understanding. Pass rates are reported per
script and must not fall below the stored baseline in baseline.yaml.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import pytest
import yaml

from kisan.understanding.dictionary import Dictionary
from kisan.understanding.script import detect_script

HERE = Path(__file__).resolve().parent
REFERENCE = HERE.parents[1] / "data" / "reference"

pytestmark = pytest.mark.eval
SC001_MIN = 0.90


def _load(name: str) -> Any:
    return yaml.safe_load((HERE / name).read_text(encoding="utf-8"))


def _check(case: dict[str, Any], dictionary: Dictionary) -> bool:
    result = dictionary.extract(case["text"])
    expect = case["expect"]
    if "intent" in expect and result.intent != expect["intent"]:
        return False
    if "crop_ids" in expect and result.crop_ids != expect["crop_ids"]:
        return False
    if "mandi_ids" in expect and result.mandi_ids != expect["mandi_ids"]:
        return False
    return all(
        forbidden not in result.crop_ids + result.mandi_ids
        for forbidden in case.get("forbidden_ids", [])
    )


def _is_clear_question(case: dict[str, Any]) -> bool:
    """SC-001 counts questions that name both a supported crop and a supported mandi."""
    expect = case["expect"]
    return bool(expect.get("crop_ids")) and bool(expect.get("mandi_ids"))


def test_golden_set_meets_baseline() -> None:
    cases = _load("golden.yaml")["cases"]
    baseline = _load("baseline.yaml")
    dictionary = Dictionary.from_reference(REFERENCE)

    totals: dict[str, int] = defaultdict(int)
    passed: dict[str, int] = defaultdict(int)
    clear_total = clear_passed = 0
    failures: list[str] = []
    for case in cases:
        script = case.get("script") or detect_script(case["text"])
        totals[script] += 1
        ok = _check(case, dictionary)
        if _is_clear_question(case):
            clear_total += 1
            clear_passed += ok
        if ok:
            passed[script] += 1
        else:
            failures.append(f"[{script}] {case['text']!r} -> {dictionary.extract(case['text'])}")

    rates = {script: passed[script] / totals[script] for script in totals}
    print("\neval pass rates:", {s: f"{r:.0%} ({passed[s]}/{totals[s]})" for s, r in rates.items()})
    print(f"SC-001 clear questions understood in one message: "
          f"{clear_passed / clear_total:.0%} ({clear_passed}/{clear_total})")
    for failure in failures:
        print("  FAIL", failure)
    assert clear_passed / clear_total >= SC001_MIN

    for script, minimum in baseline["min_pass_rate"].items():
        assert totals[script] > 0, f"no eval cases for {script}"
        assert rates[script] >= minimum, f"{script}: {rates[script]:.0%} < baseline {minimum:.0%}"


def test_cases_are_well_formed() -> None:
    for case in _load("golden.yaml")["cases"]:
        assert case["text"].strip()
        assert case["expect"], case["text"]
        assert set(case["expect"]) <= {"intent", "crop_ids", "mandi_ids"}, case["text"]
