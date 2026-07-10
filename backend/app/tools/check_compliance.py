"""Deterministic compliance checking for BeautyAgent drafts."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from strands import tool
except ImportError:
    def tool(func=None, **_kwargs):
        if func is None:
            return lambda wrapped: wrapped

        return func


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
RULES_PATH = DATA_DIR / "compliance_rules.json"


@lru_cache(maxsize=1)
def load_compliance_rules() -> list[dict[str, str]]:
    with RULES_PATH.open(encoding="utf-8") as rules_file:
        payload = json.load(rules_file)

    return payload["rules"]


def _replace_case_insensitive(text: str, phrase: str, replacement: str) -> str:
    output = text
    search_start = 0
    pattern = _phrase_pattern(phrase)

    while True:
        match = pattern.search(output, search_start)
        if match is None:
            return output

        if _is_negated_match(output, match.start()):
            search_start = match.end()
            continue

        match_start = match.start()
        match_end = match.end()
        output = output[:match_start] + replacement + output[match_end:]
        search_start = match_start + len(replacement)


def _phrase_pattern(phrase: str) -> re.Pattern[str]:
    """Match whole phrase spans without catching substrings like cure/manicure."""
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(phrase)}(?![A-Za-z0-9])",
        re.IGNORECASE,
    )


def _is_negated_match(text: str, match_start: int) -> bool:
    prefix = text[max(0, match_start - 30):match_start].lower()
    return bool(re.search(r"\b(no|without|avoid|never)\s+$", prefix))


def _has_active_match(text: str, phrase: str) -> bool:
    pattern = _phrase_pattern(phrase)
    return any(not _is_negated_match(text, match.start()) for match in pattern.finditer(text))


def check_compliance(text: str) -> dict[str, Any]:
    """Scan text for deterministic MVP compliance risks."""
    flagged_phrases: list[str] = []
    explanations: list[str] = []
    safe_output = text

    for rule in load_compliance_rules():
        phrase = rule["phrase"]
        if not _has_active_match(text, phrase):
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


@tool
def check_compliance_tool(text: str) -> dict[str, Any]:
    """Strands-compatible tool wrapper around deterministic compliance scanning."""
    return check_compliance(text)
