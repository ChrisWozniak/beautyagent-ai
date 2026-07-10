"""
Transform backend/app/data/source/compliance_rules.source.json into the runtime
phrase-substitution dictionary at backend/app/data/compliance_rules.json.

Run from the repo root:
    python -m backend.scripts.build_compliance_rules

Output shape expected by the deterministic scanner:
    {"rules": [{"phrase": "...", "replacement": "...", "explanation": "..."}]}
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "backend/app/data/source/compliance_rules.source.json"
OUTPUT = ROOT / "backend/app/data/compliance_rules.json"

# Rules without banned_phrases are validation- or evidence-aware checks that
# require formulation documentation, third-party test results, or per-SKU
# review — not simple phrase substitution. Deferred to Phase 2.
#   hypoallergenic_claim       — requires HRIPT test result reference
#   eye_area_pigment_glitter_usage — requires per-SKU eye-safety review
#   color_additive_labeling    — requires per-SKU/market labeling verification
SKIP_RULE_IDS = {
    "hypoallergenic_claim",
    "eye_area_pigment_glitter_usage",
    "color_additive_labeling",
}

# Unified phrase → replacement dictionary covering all runtime phrases.
# safe_framing fields in the source file are instructional guidance, not literal
# substitutes — every replacement must be explicitly mapped here instead.
# KeyError on an unmapped phrase is intentional: fail loudly, never silently skip.
PHRASE_REPLACEMENTS: dict[str, str] = {
    # disease_claims
    "cures acne": "helps care for acne-prone skin",
    "heals acne": "helps care for acne-prone skin",
    "clears acne": "helps care for acne-prone skin",
    "heals eczema": "gentle on eczema-prone skin",
    "cured their eczema": "said it felt gentle on eczema-prone skin",
    "say goodbye to eczema": "support eczema-prone skin",
    "eczema-free": "calmer-looking",
    "free of flare-ups": "calmer-looking",
    "stopped flare-ups for good": "helped their skin look calmer",
    "eliminates redness": "helps calm the look of redness",
    "gets rid of redness completely": "helps calm the look of redness",
    "repairs skin permanently": "helps support skin's natural resilience",
    "heals your skin barrier overnight": "helps support your skin barrier",
    "repairs your barrier overnight": "helps support your skin barrier",
    "repairs the skin barrier overnight": "helps support the skin barrier",
    "repairs your barrier while you sleep": "helps support your skin barrier",
    "fixes what's broken in your skin's defenses by morning": "helps support your skin barrier",
    "stops flare-ups before they start": "helps skin look calm and comfortable",
    "clears up eczema flare-ups": "helps calm the look of stressed skin",
    "clear up skin irritation": "helps skin look calm",
    "calm and clear up skin irritation": "helps skin look calm and comfortable",
    "cure": "help with",
    "treat eczema": "safe for eczema-prone skin",
    "treat rosacea": "safe for rosacea-prone skin",
    "gets rid of rosacea": "helps calm the look of redness",
    # antimicrobial_ingredient_claims
    "sanitizer": "purifier",
    "disinfectant": "purifier",
    "disinfects": "purifies",
    "kills bacteria": "calms skin",
    "kills germs": "refreshes skin",
    "antibacterial": "refreshing",
    "antimicrobial": "refreshing",
    "sterilizes": "refreshes",
    # medical_efficacy_claims
    "medically proven": "formulated to help",
    "clinically proven": "formulated to help",
    "proven to boost lip fullness": "designed for a fuller-looking shine",
    "toxin-free": "thoughtfully formulated",
    "chemical-free": "thoughtfully formulated",
    "anti-aging miracle": "helps skin look and feel healthier",
    "reverses aging": "helps support a smoother-looking complexion",
    "reverses fine lines": "helps soften the look of fine lines",
    "collagen boosting": "helps support smoother-looking skin",
    "boosts your skin's collagen production": "helps skin look smoother",
    "reduces puffiness and dark circles": "helps refresh the look of the eye area",
    "visibly reduces puffiness and dark circles": "helps refresh the look of the eye area",
    # third_party_certification_claims (4)
    "National Eczema Association recommends": "follows National Eczema Association ingredient guidelines",
    "National Eczema Association endorses": "follows National Eczema Association ingredient guidelines",
    "NEA recommends": "follows NEA ingredient guidelines",
    "NEA endorses": "follows NEA ingredient guidelines",
    # dermatologist_testing_claims
    "dermatologist recommended": "gentle on skin",
    "dermatologist endorsed": "gentle on skin",
    "dermatologist prescribed": "gentle on skin",
}


def build() -> None:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    runtime_rules: list[dict[str, str]] = []

    for rule in source["rules"]:
        rule_id = rule["id"]

        if rule_id in SKIP_RULE_IDS:
            continue

        banned_phrases = rule.get("banned_phrases")
        if not banned_phrases:
            continue

        description = rule["description"]

        for phrase in banned_phrases:
            replacement = PHRASE_REPLACEMENTS[phrase]  # KeyError = missing mapping, fix it
            runtime_rules.append({
                "phrase": phrase,
                "replacement": replacement,
                "explanation": description,
            })

    output = {"rules": runtime_rules}
    OUTPUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(runtime_rules)} rules to {OUTPUT}")


if __name__ == "__main__":
    build()
