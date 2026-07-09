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

# Explicit replacement map for rules that have no safe_framing field.
EXPLICIT_REPLACEMENTS: dict[str, str] = {
    "medically proven": "formulated to help",
    "clinically proven": "formulated to help",
    "toxin-free": "thoughtfully formulated",
    "chemical-free": "thoughtfully formulated",
    "anti-aging miracle": "helps skin look and feel healthier",
    "reverses aging": "helps support a smoother-looking complexion",
    "collagen boosting": "helps support smoother-looking skin",
    "dermatologist recommended": "gentle on skin",
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
        safe_framing = rule.get("safe_framing")

        for phrase in banned_phrases:
            if safe_framing:
                replacement = safe_framing
            else:
                replacement = EXPLICIT_REPLACEMENTS[phrase]

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
