"""Backend-only live `/generate` smoke test.

Run from the repository root:

    python backend/scripts/smoke_generate_live.py

Requires:
    USE_LLM_DRAFTING=true
    ANTHROPIC_API_KEY=...

The script calls the FastAPI route through TestClient, so it verifies the same
response shape the frontend will consume while still avoiding a local server.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.agent.beauty_agent import draft_channel_copy
from backend.app.config import get_settings
from backend.app.main import app
from backend.app.models.request_models import GenerateRequest


def main() -> int:
    settings = get_settings()
    if not settings.use_llm_drafting:
        print("Live /generate smoke test skipped: USE_LLM_DRAFTING is false.")
        print("Set USE_LLM_DRAFTING=true and ANTHROPIC_API_KEY to test live endpoint drafting.")
        return 2

    if not settings.anthropic_api_key and not settings.openrouter_api_key:
        print("Live /generate smoke test skipped: ANTHROPIC_API_KEY or OPENROUTER_API_KEY is not configured.")
        return 2

    request = GenerateRequest(
        brandId="tower_28",
        productName="SOS Daily Rescue Facial Spray",
        coreActives="Hypochlorous Acid",
        brief="Draft a compliant Instagram caption for sensitive-looking skin. Avoid medical claims.",
        channels=["instagram"],
    )
    deterministic_fallback = draft_channel_copy(request, "instagram")

    response = TestClient(app).post("/generate", json=request.model_dump())
    payload = response.json()

    if response.status_code != 200 or payload.get("error") is not None:
        print(f"Live /generate smoke test failed: {response.status_code}")
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 1

    results = payload.get("results", [])
    if len(results) != 1:
        print(f"Live /generate smoke test failed: expected 1 result, got {len(results)}.")
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 1

    result = results[0]
    if result.get("generation_status") != "completed" or result.get("error") is not None:
        print("Live /generate smoke test failed: channel did not complete.")
        print(json.dumps(payload, indent=2, ensure_ascii=True))
        return 1

    if result.get("raw_draft") == deterministic_fallback:
        print("Live /generate smoke test failed: endpoint fell back to deterministic mock drafting.")
        return 1

    model = settings.anthropic_model_sonnet if settings.anthropic_api_key else settings.openrouter_model
    print("Live /generate smoke test passed.")
    print(f"Model: {model}")
    print(f"Channel: {result['channel']}")
    print(f"Compliance: {result['compliance_status']}")
    print(f"Draft preview: {result['raw_draft'][:240]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
