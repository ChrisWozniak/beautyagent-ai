"""Deterministic compliance checking for BeautyAgent drafts."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RULES_PATH = DATA_DIR / "compliance_rules.json"


@lru_cache(maxsize=1)
def load_compliance_rules() -> list[dict[str, str]]:
    with RULES_PATH.open(encoding="utf-8") as rules_file:
        payload = json.load(rules_file)

    return payload["rules"]


def _replace_case_insensitive(text: str, phrase: str, replacement: str) -> str:
    lower_text = text.lower()
    lower_phrase = phrase.lower()
    output = text
    search_start = 0

    while True:
        match_start = lower_text.find(lower_phrase, search_start)
        if match_start == -1:
            return output

        match_end = match_start + len(phrase)
        output = output[:match_start] + replacement + output[match_end:]
        lower_text = output.lower()
        search_start = match_start + len(replacement)


def check_compliance(text: str) -> dict[str, Any]:
    """Scan text for deterministic MVP compliance risks."""
    flagged_phrases: list[str] = []
    explanations: list[str] = []
    safe_output = text
    lowered_text = text.lower()

    for rule in load_compliance_rules():
        phrase = rule["phrase"]
        if phrase.lower() not in lowered_text:
            continue

        flagged_phrases.append(phrase)
        explanations.append(rule["explanation"])
        safe_output = _replace_case_insensitive(
            safe_output,
            phrase,
            rule["replacement"],
        )

    if not flagged_phrases:
        return {
            "compliance_status": "PASSED",
            "flagged_phrases": [],
            "explanation": "",
            "detection_source": None,
            "final_safe_output": text,
        }

    return {
        "compliance_status": "FAILED",
        "flagged_phrases": flagged_phrases,
        "explanation": " ".join(explanations),
        "detection_source": "deterministic",
        "final_safe_output": safe_output,
    }
