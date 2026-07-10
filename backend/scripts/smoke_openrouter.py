"""Backend-only LiteLLM/OpenRouter smoke test.

Run from the repository root:

    python backend/scripts/smoke_openrouter.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from backend.app.agent.beauty_agent import load_brand_configs
from backend.app.agent.llm_client import LLMDraftError, generate_draft_with_llm
from backend.app.config import get_settings
from backend.app.models.request_models import GenerateRequest


def main() -> int:
    settings = get_settings()
    if not settings.use_llm_drafting:
        print("OpenRouter smoke test skipped: USE_LLM_DRAFTING is false.")
        print("Set USE_LLM_DRAFTING=true and OPENROUTER_API_KEY to test live drafting.")
        return 2

    if not settings.openrouter_api_key:
        print("OpenRouter smoke test skipped: OPENROUTER_API_KEY is not configured.")
        return 2

    request = GenerateRequest(
        brandId="tower_28",
        productName="SOS Daily Rescue Facial Spray",
        coreActives="Hypochlorous Acid",
        brief="Draft one compliant Instagram caption for sensitive-looking skin.",
        channels=["instagram"],
    )
    brand_config = load_brand_configs()[request.brandId]

    try:
        draft = generate_draft_with_llm(
            request=request,
            channel="instagram",
            brand_config=brand_config,
            safe_claim="helps calm the look of stressed skin",
            settings=settings,
        )
    except LLMDraftError as exc:
        print(f"OpenRouter smoke test failed: {exc}")
        return 1

    print("OpenRouter smoke test passed.")
    print(f"Model: {settings.openrouter_model}")
    print(draft)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
