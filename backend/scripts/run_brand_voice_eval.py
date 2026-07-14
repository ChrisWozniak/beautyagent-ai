"""Run brand voice calibration cases through the Brand Voice Agent.

Run from the repository root:

    python backend/scripts/run_brand_voice_eval.py
    python backend/scripts/run_brand_voice_eval.py --start 1 --end 3 --compact
    python backend/scripts/run_brand_voice_eval.py --case-id tower28_good_clean_fun_instagram_on_voice
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "backend/evals/brand_voice_calibration_cases.json"

sys.path.insert(0, str(ROOT))

from backend.app.agent.beauty_agent import load_brand_configs
from backend.app.models.request_models import Channel
from backend.app.tools.check_brand_voice import check_brand_voice


VALID_VOICE_STATUSES = {"ON_VOICE", "DRIFTED"}
VoiceChecker = Callable[[str, str, dict[str, Any], str], dict[str, Any]]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run BeautyAgent brand voice calibration cases.",
    )
    parser.add_argument(
        "--start",
        type=int,
        help="1-based first case number to run, inclusive.",
    )
    parser.add_argument(
        "--end",
        type=int,
        help="1-based last case number to run, inclusive.",
    )
    parser.add_argument(
        "--case-id",
        action="append",
        dest="case_ids",
        help="Run one case by id. Repeat to run multiple specific cases.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Print one result line per case with no reason details.",
    )
    return parser.parse_args(argv)


def validate_case(case: dict[str, Any]) -> None:
    if "id" not in case:
        raise ValueError("Brand voice case is missing id.")

    required_fields = ["brandId", "channel", "expected_voice_status", "text"]
    for field in required_fields:
        if field not in case:
            raise ValueError(f"{case['id']}: missing {field}.")

    if case["expected_voice_status"] not in VALID_VOICE_STATUSES:
        raise ValueError(
            f"{case['id']}: expected_voice_status must be ON_VOICE or DRIFTED."
        )

    if case["channel"] not in {"tiktok", "instagram", "email"}:
        raise ValueError(f"{case['id']}: channel must be tiktok, instagram, or email.")

    if not isinstance(case["text"], str) or not case["text"].strip():
        raise ValueError(f"{case['id']}: text must be a non-empty string.")


def select_cases(
    cases: list[dict[str, Any]],
    start: int | None = None,
    end: int | None = None,
    case_ids: list[str] | None = None,
) -> list[tuple[int, dict[str, Any]]]:
    """Return selected cases with their original 1-based case numbers."""
    if start is not None and start < 1:
        raise ValueError("--start must be 1 or greater.")

    if end is not None and end < 1:
        raise ValueError("--end must be 1 or greater.")

    if start is not None and end is not None and start > end:
        raise ValueError("--start cannot be greater than --end.")

    selected = list(enumerate(cases, start=1))

    if start is not None:
        selected = [(index, case) for index, case in selected if index >= start]

    if end is not None:
        selected = [(index, case) for index, case in selected if index <= end]

    if case_ids:
        wanted = set(case_ids)
        selected = [
            (index, case)
            for index, case in selected
            if case["id"] in wanted
        ]
        found = {case["id"] for _, case in selected}
        missing = sorted(wanted - found)
        if missing:
            raise ValueError(f"Unknown --case-id value(s): {', '.join(missing)}")

    return selected


def _shorten(text: str | None, limit: int = 220) -> str:
    if not text:
        return ""

    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}..."


def _load_cases() -> list[dict[str, Any]]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]


def run(
    argv: list[str] | None = None,
    voice_checker: VoiceChecker = check_brand_voice,
) -> int:
    args = parse_args(argv)
    all_cases = _load_cases()
    cases = select_cases(all_cases, args.start, args.end, args.case_ids)
    brand_configs = load_brand_configs()
    failures: list[str] = []

    if not cases:
        print("No cases selected.")
        return 1

    for case_number, case in cases:
        validate_case(case)
        brand_id = case["brandId"]
        result = voice_checker(
            case["text"],
            brand_id,
            brand_configs[brand_id],
            case["channel"],
        )

        expected = case["expected_voice_status"]
        actual = result["voice_status"]
        passed = actual == expected
        result_text = "PASS" if passed else "FAIL"
        print(
            f"{result_text} #{case_number} {case['id']}: "
            f"expected {expected}, got {actual}; "
            f"confidence={result['voice_confidence']}"
        )

        if not args.compact:
            print(f"  - channel: {case['channel']}")
            print(f"  - reason: {_shorten(result.get('voice_reason'))}")

        if not passed:
            failures.append(case["id"])

    print(f"\n{len(cases) - len(failures)}/{len(cases)} selected cases passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
