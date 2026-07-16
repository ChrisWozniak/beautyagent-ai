"""Run backend red-team eval cases through the FastAPI app.

Run from the repository root:

    python backend/scripts/run_red_team_eval.py
    python backend/scripts/run_red_team_eval.py --start 1 --end 5 --compact
    python backend/scripts/run_red_team_eval.py --case-id risky_collagen_boost_claim
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "backend/evals/red_team_cases.json"

sys.path.insert(0, str(ROOT))

from backend.app.agent.llm_client import reset_llm_usage
from backend.app.main import app
from backend.scripts.usage_report import print_llm_usage_report


VALID_STATUSES = {"PASSED", "FAILED"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run BeautyAgent backend red-team eval cases through /generate.",
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
        help="Print one result line per case with no per-channel details.",
    )
    parser.add_argument(
        "--mock-brand-voice",
        action="store_true",
        help=(
            "Use deterministic drafting and bypass the live Brand Voice Agent "
            "with an ON_VOICE result so this runner measures deterministic "
            "compliance outcomes only."
        ),
    )
    return parser.parse_args(argv)


def expected_statuses_for_case(case: dict) -> dict[str, str]:
    """Return expected compliance status by channel for a red-team case."""
    channels = case["request"]["channels"]

    if "expected_by_channel" in case:
        expected_by_channel = case["expected_by_channel"]
        return {channel: expected_by_channel[channel] for channel in channels}

    expected_status = case["expected_status"]
    return {channel: expected_status for channel in channels}


def validate_case(case: dict) -> None:
    if "id" not in case:
        raise ValueError("Red-team case is missing id.")

    if "request" not in case:
        raise ValueError(f"{case['id']}: missing request.")

    channels = case["request"].get("channels")
    if not isinstance(channels, list) or not channels:
        raise ValueError(f"{case['id']}: request.channels must be a non-empty list.")

    has_simple_expected = "expected_status" in case
    has_channel_expected = "expected_by_channel" in case
    if has_simple_expected == has_channel_expected:
        raise ValueError(
            f"{case['id']}: provide exactly one of expected_status or expected_by_channel."
        )

    expected_by_channel = expected_statuses_for_case(case)
    if set(expected_by_channel) != set(channels):
        raise ValueError(f"{case['id']}: expected channels must match request.channels.")

    invalid_statuses = [
        status
        for status in expected_by_channel.values()
        if status not in VALID_STATUSES
    ]
    if invalid_statuses:
        raise ValueError(
            f"{case['id']}: expected statuses must be PASSED or FAILED."
        )


def select_cases(
    cases: list[dict],
    start: int | None = None,
    end: int | None = None,
    case_ids: list[str] | None = None,
) -> list[tuple[int, dict]]:
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


def _shorten(text: str | None, limit: int = 180) -> str:
    if not text:
        return ""

    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}..."


def _print_case_details(payload: dict, expected_by_channel: dict[str, str]) -> None:
    for result in payload["results"]:
        channel = result["channel"]
        flags = result.get("flagged_phrases") or []
        explanation = _shorten(result.get("explanation"))
        print(
            f"  - {channel}: expected {expected_by_channel[channel]}, "
            f"got {result['compliance_status']}; flags={flags}; "
            f"explanation={explanation}"
        )


def _mock_on_voice_result(
    _text: str,
    _brand_id: str,
    _brand_config: dict,
    _channel: str,
) -> dict:
    return {
        "voice_status": "ON_VOICE",
        "voice_confidence": 1.0,
        "voice_reason": "Mocked ON_VOICE result for deterministic compliance eval.",
    }


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.mock_brand_voice:
        os.environ["USE_LLM_DRAFTING"] = "false"

    reset_llm_usage()
    all_cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    cases = select_cases(all_cases, args.start, args.end, args.case_ids)
    client = TestClient(app)
    failures: list[str] = []

    if not cases:
        print("No cases selected.")
        return 1

    for case_number, case in cases:
        validate_case(case)
        if args.mock_brand_voice:
            with patch(
                "backend.app.agent.beauty_agent.check_brand_voice",
                side_effect=_mock_on_voice_result,
            ):
                response = client.post("/generate", json=case["request"])
        else:
            response = client.post("/generate", json=case["request"])
        payload = response.json()

        if response.status_code != 200 or payload["error"] is not None:
            failure = f"{case['id']}: request failed with {payload['error']}"
            print(f"FAIL #{case_number} {failure}")
            failures.append(failure)
            continue

        actual_by_channel = {
            result["channel"]: result["compliance_status"]
            for result in payload["results"]
        }
        expected_by_channel = expected_statuses_for_case(case)
        passed = actual_by_channel == expected_by_channel
        result_text = "PASS" if passed else "FAIL"
        print(
            f"{result_text} #{case_number} {case['id']}: "
            f"expected {expected_by_channel}, got {actual_by_channel}"
        )

        if not args.compact:
            _print_case_details(payload, expected_by_channel)

        if not passed:
            failures.append(case["id"])

    print(f"\n{len(cases) - len(failures)}/{len(cases)} selected cases passed.")
    print_llm_usage_report()
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
