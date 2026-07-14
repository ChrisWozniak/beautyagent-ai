# Week 2 Backend Readiness Summary

Date: July 14, 2026
Branch: `week-2`

## Status

Backend Week 2 is complete and ready for Jillian's frontend integration testing.

Latest pushed backend handoff commit:

```text
4036766 Add Week 2 demo smoke runner
```

Backend base URL for deployed frontend testing:

```text
https://beautyagent-ai.onrender.com
```

Health check verified on July 14, 2026:

```json
{"status": "ok"}
```

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

Result: `67/67 passed`

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

Latest full demo smoke live Sonnet calibration run:

- calls: `6`
- prompt tokens: `2,539`
- completion tokens: `559`
- total tokens: `3,098`
- estimated cost: `$0.016002`

Local ledger grand total after the latest run:

- calls: `22`
- total tokens: `10,489`
- estimated cost: `$0.051831`

The local ledger file is ignored by git:

```text
backend/logs/llm_usage_local.jsonl
```

Do not commit API keys or local usage logs.

## Ready For Jill / Frontend

Slack-ready handoff message:

```text
backend/evals/JILL_FRONTEND_HANDOFF_SLACK.md
```

Jillian can set her frontend API base URL to:

```text
VITE_API_URL=https://beautyagent-ai.onrender.com
```

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

Render note: the Blueprint default has `USE_LLM_DRAFTING=false`, which is appropriate for deterministic frontend contract/UI testing. For live Claude drafting and Brand Voice Agent testing on Render, set `USE_LLM_DRAFTING=true` and configure `ANTHROPIC_API_KEY` in Render environment variables.

## Known Limitations

The current compliance eval is deterministic and token-safe when run with `--mock-brand-voice`.

The Week 2 PRD describes a future/expanded Haiku compliance LLM audit path. The backend keeps model config for Haiku, but the current validated compliance pass rate is based on deterministic rule scanning plus the final deterministic backstop.

Autonomous regeneration loops are not implemented. Week 2 routes uncertain or drifted results to human review/resubmit instead.

## Recommended Pre-Demo Commands

Run the full backend smoke from the repository root:

```powershell
python backend/scripts/run_demo_smoke.py
```

This runs the same sequence as:

```powershell
python -m unittest discover -s backend\tests -v
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
python backend/scripts/run_brand_voice_eval.py --compact
```

Only the brand voice calibration command is expected to spend Claude/Sonnet tokens.

For a token-free local check that skips the live Sonnet calibration step:

```powershell
python backend/scripts/run_demo_smoke.py --skip-live-brand-voice
```

Latest full demo smoke result:

- backend unit tests: `67/67 passed`
- red-team compliance eval: `20/20 passed`
- live Sonnet brand voice calibration: `6/6 passed`
