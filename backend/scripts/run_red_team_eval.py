"""Run backend red-team eval cases through the FastAPI app.

Run from the repository root:

    python backend/scripts/run_red_team_eval.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "backend/evals/red_team_cases.json"

sys.path.insert(0, str(ROOT))

from backend.app.main import app


VALID_STATUSES = {"PASSED", "FAILED"}


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


def run() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    client = TestClient(app)
    failures: list[str] = []

    for case in cases:
        validate_case(case)
        response = client.post("/generate", json=case["request"])
        payload = response.json()

        if response.status_code != 200 or payload["error"] is not None:
            failures.append(f"{case['id']}: request failed with {payload['error']}")
            continue

        actual_by_channel = {
            result["channel"]: result["compliance_status"]
            for result in payload["results"]
        }
        expected_by_channel = expected_statuses_for_case(case)
        passed = actual_by_channel == expected_by_channel
        result_text = "PASS" if passed else "FAIL"
        print(
            f"{result_text} {case['id']}: "
            f"expected {expected_by_channel}, got {actual_by_channel}"
        )

        if not passed:
            failures.append(case["id"])

    print(f"\n{len(cases) - len(failures)}/{len(cases)} cases passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
