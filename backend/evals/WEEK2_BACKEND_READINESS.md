# Week 2 Backend Readiness Summary

Date: July 14, 2026
Branch: `week-2`

## Status

Backend Week 2 is ready for frontend integration and demo validation.

The backend now supports the Week 2 channel loop:

- draft generation with deterministic fallback
- Brand Voice Agent gate using Sonnet
- conditional compliance routing after voice passes
- deterministic compliance scan and final backstop
- `NEEDS_HUMAN_REVIEW` response shape
- per-channel independence
- local LLM usage tracking with grand totals

## Verified Results

Backend unit test suite:

```powershell
python -m unittest discover -s backend\tests -v
```

Result: `65/65 passed`

Week 2 red-team compliance eval:

```powershell
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
```

Result: `20/20 passed`

This run uses deterministic drafting and a mocked `ON_VOICE` Brand Voice Agent result so it measures deterministic compliance outcomes without spending Claude/Sonnet tokens.

Week 2 brand voice calibration eval:

```powershell
python backend/scripts/run_brand_voice_eval.py --compact
```

Result: `6/6 passed`

This run intentionally uses Sonnet because it validates brand voice accuracy, confidence calibration, and reason quality.

## Latest LLM Usage Snapshot

Latest brand voice calibration run:

- calls: `6`
- prompt tokens: `2,539`
- completion tokens: `557`
- total tokens: `3,096`
- estimated cost: `$0.015972`

Local ledger grand total after the latest run:

- calls: `16`
- total tokens: `7,391`
- estimated cost: `$0.035829`

The local ledger file is ignored by git:

```text
backend/logs/llm_usage_local.jsonl
```

Do not commit API keys or local usage logs.

## Ready For Jill / Frontend

The frontend can rely on the `/generate` response contract for:

- `voice_status`
- `voice_confidence`
- `voice_reason`
- `compliance_status`
- `compliance_confidence`
- `detection_source`
- `escalation_trigger`
- `final_safe_output`
- channel-level `error`

Expected Week 2 statuses include:

- `PASSED`
- `FAILED`
- `NEEDS_HUMAN_REVIEW`

Per-channel independence is implemented: one channel can fail, drift, or route to human review without blocking sibling channels.

## Known Limitations

The current compliance eval is deterministic and token-safe when run with `--mock-brand-voice`.

The Week 2 PRD describes a future/expanded Haiku compliance LLM audit path. The backend keeps model config for Haiku, but the current validated compliance pass rate is based on deterministic rule scanning plus the final deterministic backstop.

Autonomous regeneration loops are not implemented. Week 2 routes uncertain or drifted results to human review/resubmit instead.

## Recommended Pre-Demo Commands

Run these from the repository root:

```powershell
python -m unittest discover -s backend\tests -v
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
python backend/scripts/run_brand_voice_eval.py --compact
```

Only the brand voice calibration command is expected to spend Claude/Sonnet tokens.
