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


def run() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    client = TestClient(app)
    failures: list[str] = []

    for case in cases:
        response = client.post("/generate", json=case["request"])
        payload = response.json()

        if response.status_code != 200 or payload["error"] is not None:
            failures.append(f"{case['id']}: request failed with {payload['error']}")
            continue

        statuses = {result["compliance_status"] for result in payload["results"]}
        expected = case["expected_status"]
        passed = statuses == {expected}
        result_text = "PASS" if passed else "FAIL"
        print(f"{result_text} {case['id']}: expected {expected}, got {sorted(statuses)}")

        if not passed:
            failures.append(case["id"])

    print(f"\n{len(cases) - len(failures)}/{len(cases)} cases passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run())
