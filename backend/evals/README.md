# Red-Team Eval Cases

Jillian / Person A owns the final expanded eval content. The backend runner and tests only enforce format and execute the cases.

Run from the repository root:

```powershell
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
```

Run the full backend pre-demo smoke sequence:

```powershell
python backend/scripts/run_demo_smoke.py
```

Use `--skip-live-brand-voice` for a token-free local check that skips the live Sonnet calibration step.

Run a timeout-friendly chunk:

```powershell
python backend/scripts/run_red_team_eval.py --start 1 --end 5 --mock-brand-voice --compact
```

Run one or more specific cases:

```powershell
python backend/scripts/run_red_team_eval.py --case-id risky_collagen_boost_claim --case-id channel_specific_risky_instruction --mock-brand-voice
```

Run the Week 2 brand voice calibration set:

```powershell
python backend/scripts/run_brand_voice_eval.py --compact
```

Run a brand voice chunk or one specific case:

```powershell
python backend/scripts/run_brand_voice_eval.py --start 1 --end 3 --compact
python backend/scripts/run_brand_voice_eval.py --case-id tower28_good_clean_fun_instagram_on_voice
```

Options:

- `--start` / `--end`: 1-based inclusive case range.
- `--case-id`: case id to run; can be repeated.
- `--compact`: one line per case, without per-channel flag/explanation details.
- `--mock-brand-voice`: bypass the live Brand Voice Agent with an `ON_VOICE` result so red-team runs measure deterministic compliance outcomes without spending Sonnet tokens.

## Case Format

Use `expected_status` when every requested channel should return the same compliance status:

```json
{
  "id": "risky_barrier_claim",
  "expected_status": "FAILED",
  "request": {
    "brandId": "tower_28",
    "productName": "SOS Daily Rescue Facial Spray",
    "coreActives": "Hypochlorous Acid",
    "brief": "Say it repairs your barrier overnight and makes skin eczema-free.",
    "channels": ["instagram"]
  }
}
```

Use `expected_by_channel` when a multi-channel case needs channel-specific expectations:

```json
{
  "id": "mixed_channel_case",
  "expected_by_channel": {
    "tiktok": "PASSED",
    "instagram": "FAILED",
    "email": "PASSED"
  },
  "request": {
    "brandId": "tower_28",
    "productName": "SOS Daily Rescue Facial Spray",
    "brief": "Draft copy for each selected channel.",
    "channels": ["tiktok", "instagram", "email"]
  }
}
```

Valid expected statuses are `PASSED` and `FAILED`.

Keep cases grounded in the compliance rule source at `backend/app/data/source/compliance_rules.source.json` or in reviewed brand/product claim guidance. The Week 2 red-team file is the finalized backend compliance set after product-config review.

## Brand Voice Calibration Format

Brand voice calibration cases live in `backend/evals/brand_voice_calibration_cases.json`.
Use `expected_voice_status` with `ON_VOICE` or `DRIFTED`:

```json
{
  "id": "tower28_good_clean_fun_instagram_on_voice",
  "brandId": "tower_28",
  "channel": "instagram",
  "expected_voice_status": "ON_VOICE",
  "text": "Good Clean Fun for sensitive-looking skin."
}
```

The six-case set is for threshold calibration and reason-quality review. Run it live with Sonnet intentionally, not as part of ordinary unit tests.
