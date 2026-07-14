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


SMOKE_CASES = [
    GenerateRequest(
        brandId="tower_28",
        productName="SOS Daily Rescue Facial Spray",
        coreActives="Hypochlorous Acid",
        brief="Draft a compliant Instagram caption for sensitive-looking skin. Avoid medical claims.",
        channels=["instagram"],
    ),
    GenerateRequest(
        brandId="half_magic",
        productName="Magic Drip Glitter Lipgloss",
        coreActives="Vitamin E, Jojoba Oil",
        brief=(
            "Draft playful TikTok copy about glitter payoff and non-sticky shine "
            "for a night-out look. Keep it bold and casual."
        ),
        channels=["tiktok"],
    ),
]


def safe_console_text(text: str, limit: int = 240) -> str:
    """Return an ASCII-safe one-line preview for Windows consoles."""
    normalized = " ".join(text.split())
    preview = normalized[:limit]
    return preview.encode("ascii", errors="backslashreplace").decode("ascii")


def run_smoke_case(client: TestClient, request: GenerateRequest) -> tuple[bool, str]:
    channel = request.channels[0]
    deterministic_fallback = draft_channel_copy(request, channel)
    response = client.post("/generate", json=request.model_dump())
    payload = response.json()
    label = f"{request.brandId}/{channel}"

    if response.status_code != 200 or payload.get("error") is not None:
        return (
            False,
            f"{label}: failed with HTTP {response.status_code}\n"
            f"{json.dumps(payload, indent=2, ensure_ascii=True)}",
        )

    results = payload.get("results", [])
    if len(results) != 1:
        return (
            False,
            f"{label}: expected 1 result, got {len(results)}.\n"
            f"{json.dumps(payload, indent=2, ensure_ascii=True)}",
        )

    result = results[0]
    if result.get("generation_status") != "completed" or result.get("error") is not None:
        return (
            False,
            f"{label}: channel did not complete.\n"
            f"{json.dumps(payload, indent=2, ensure_ascii=True)}",
        )

    if result.get("raw_draft") == deterministic_fallback:
        return False, f"{label}: endpoint fell back to deterministic mock drafting."

    details = [
        f"{label}: passed",
        f"  voice: {result.get('voice_status')} ({result.get('voice_confidence')})",
        f"  compliance: {result.get('compliance_status')} ({result.get('compliance_confidence')})",
        f"  escalation: {result.get('escalation_trigger')}",
        f"  draft preview: {safe_console_text(result.get('raw_draft') or '')}",
    ]
    return True, "\n".join(details)


def main() -> int:
    settings = get_settings()
    if not settings.use_llm_drafting:
        print("Live /generate smoke test skipped: USE_LLM_DRAFTING is false.")
        print("Set USE_LLM_DRAFTING=true and ANTHROPIC_API_KEY to test live endpoint drafting.")
        return 2

    if not settings.anthropic_api_key and not settings.openrouter_api_key:
        print("Live /generate smoke test skipped: ANTHROPIC_API_KEY or OPENROUTER_API_KEY is not configured.")
        return 2

    model = settings.anthropic_model_sonnet if settings.anthropic_api_key else settings.openrouter_model
    print(f"Model: {model}")

    client = TestClient(app)
    failures = 0
    for request in SMOKE_CASES:
        passed, message = run_smoke_case(client, request)
        print(message)
        if not passed:
            failures += 1

    if failures:
        print(f"Live /generate smoke test failed: {failures}/{len(SMOKE_CASES)} cases failed.")
        return 1

    print(f"Live /generate smoke test passed: {len(SMOKE_CASES)}/{len(SMOKE_CASES)} cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
