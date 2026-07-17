# BeautyAgent AI Backend

FastAPI backend for the BeautyAgent AI `/generate` endpoint.

This side of the project owns agent orchestration, compliance tooling, static backend config, and the response shape defined by the shared API contract.

## Agent Role

The backend runs a two-agent sequential pipeline. For each requested channel, the Brand Voice Agent evaluates the generated draft against the brand's enriched voice profile and returns a verdict (`ON_VOICE` or `DRIFTED`), a confidence score, and a plain-language reason. If voice confidence clears 0.75, the Compliance Agent runs next and audits for unsafe or unsupported cosmetic claims. The orchestrator merges both verdicts into one of three channel statuses: `PASSED`, `FAILED`, or `NEEDS_HUMAN_REVIEW`. All three channels run concurrently and fail independently.

## Problem It Solves

The backend helps beauty marketing teams create faster first-draft content while reducing two key risks: copy that drifts away from approved brand voice and copy that makes unsafe or unsupported cosmetic claims.

v1 returned a binary `PASSED`/`FAILED` compliance verdict with no visibility into brand voice. Copy could ship as "Compliant" while reading as generic, over-cautious, or tonally flat — with no signal to the marketer that anything was off. Agent 2.0 adds an explicit voice evaluation layer before compliance runs, so both failure modes surface as distinct, actionable signals.

## Tools Used

- FastAPI route: `/generate`
- Drafting: deterministic mock drafting by default, optional Claude/LiteLLM drafting when backend keys are configured
- Brand voice: Sonnet-backed `check_brand_voice` — new in Agent 2.0; evaluates every draft against the brand's enriched voice profile before compliance runs; returns `voice_status`, `voice_confidence`, and `voice_reason`
- Compliance: deterministic `check_compliance`, brief audit, merged audit, and final safety backstop — `compliance_confidence` now surfaced to the orchestrator instead of being discarded internally
- Orchestrator routing: merges `voice_confidence` and `compliance_confidence` against the 0.75 threshold; sets `compliance_status` and `escalation_trigger` (`"voice"` | `"compliance"` | `null`)
- Config/data: brand configs (with enriched voice profile strings), product configs, compliance rules, and runtime brand voice profile markdown files
- Validation: Pydantic request/response models with strict frontend-facing fields
- Verification: unit tests, red-team evals, brand voice calibration evals, live smoke tests, and demo smoke script
- Usage tracking: local token/cost ledger for live LLM calls

## How to Run

Start the backend from the repository root:

```powershell
uvicorn app.main:app --reload --app-dir backend
```

Run the main backend checks:

```powershell
python -m unittest discover -s backend\tests -v
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
```

Run the full handoff smoke:

```powershell
python backend/scripts/run_demo_smoke.py
```

## Local Entry Point

```powershell
uvicorn app.main:app --reload --app-dir backend
```

The frontend scaffold calls this API from `http://localhost:5173` by default. Local Vite origins are allowed through backend CORS.

Optional deployment override:

```text
FRONTEND_ORIGINS=https://your-frontend.example.com
```

Use a comma-separated list for multiple origins.

## Drafting Mode

Mock drafting is the default so frontend integration stays stable without an LLM key.

To enable LiteLLM/Claude drafting, put the key in backend-only environment config, such as `backend/.env` for local development or Render environment variables for deployment:

```text
USE_LLM_DRAFTING=true
ANTHROPIC_API_KEY=your_claude_api_key_here
ANTHROPIC_MODEL_SONNET=anthropic/claude-sonnet-4-5
ANTHROPIC_MODEL_HAIKU=anthropic/claude-haiku-4-5-20251001
LLM_TIMEOUT_SECONDS=15
LLM_MAX_TOKENS=1000
CHANNEL_TIMEOUT_SECONDS=20
```

Do not put `ANTHROPIC_API_KEY` or any provider key in React/Vite frontend files. The frontend should call FastAPI `/generate`; the backend calls Claude through LiteLLM.
`ANTHROPIC_MODEL_SONNET` is used for generation and the Brand Voice Agent (`check_brand_voice`). `ANTHROPIC_MODEL_HAIKU` is reserved for the compliance LLM audit path.

OpenRouter remains supported as a fallback provider for existing setups:

```text
USE_LLM_DRAFTING=true
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=poolside/laguna-m.1:free
LLM_TIMEOUT_SECONDS=15
LLM_MAX_TOKENS=1000
CHANNEL_TIMEOUT_SECONDS=20
```

If LLM drafting is disabled, unavailable, or misconfigured, the backend falls back to deterministic mock drafting and still returns the same `/generate` response shape.
Fallback drafts still run through the same full pipeline as LLM drafts: Brand Voice Agent → compliance audit (brief audit, merged audit, final deterministic safety backstop).
`LLM_TIMEOUT_SECONDS` limits the direct provider call. `LLM_MAX_TOKENS` caps the draft response size. `CHANNEL_TIMEOUT_SECONDS` limits the full per-channel backend pipeline and returns that channel with `generation_status: "error"` and `error.code: "TIMEOUT"` if exceeded.

Drafts are formatted for the current result cards: TikTok uses `Hook` / `Script` / `CTA`, Email uses `Subject` / `Body`, and Instagram reads as caption copy. These are formatting conventions inside the single `raw_draft` and `final_safe_output` string fields, not separate API fields.

The backend audits both the generated draft and the original marketer brief before returning a completed result. Brief-level violations can return `compliance_status: "FAILED"` even when the visible draft is clean; those explanations start with `Marketer brief also included risky language:`. Repeated explanations from the same compliance rule are deduped so UI cards do not show the same rationale multiple times.

`/generate` currently returns one full response after all requested channels complete or error. There is no streaming, polling, websocket, or mid-request progress endpoint.

Backend-only LiteLLM smoke test:

```powershell
python backend/scripts/smoke_openrouter.py
```

The smoke test calls LiteLLM directly and does not involve the frontend.
It exits as skipped unless `USE_LLM_DRAFTING=true` and either `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` is configured.

Backend-only live `/generate` smoke test:

```powershell
python backend/scripts/smoke_generate_live.py
```

This calls the FastAPI route through `TestClient`, verifies the frontend-facing response shape, and fails if the endpoint silently falls back to deterministic mock drafting.

Backend-only live Render smoke test:

```powershell
python backend/scripts/smoke_render_live.py
```

This checks the deployed Render backend for `/health`, `/version`, CORS preflight from the Week 2 Vercel preview origin, and `POST /generate` with a free-text product name. It does not change the `/generate` response contract or touch frontend files.

Backend-only red-team eval runner:

```powershell
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
```

The eval runner posts sample safe/risky cases through the FastAPI app and reports expected `PASSED`/`FAILED`/`NEEDS_HUMAN_REVIEW` outcomes. Use `--mock-brand-voice` for the Week 2 red-team compliance set so the run measures deterministic compliance behavior without spending Sonnet tokens on the Brand Voice Agent. It supports both a single `expected_status` for all requested channels and an `expected_by_channel` map for mixed multi-channel cases.

For timeout-friendly chunks or targeted reruns:

```powershell
python backend/scripts/run_red_team_eval.py --start 1 --end 5 --mock-brand-voice --compact
python backend/scripts/run_red_team_eval.py --case-id risky_collagen_boost_claim --mock-brand-voice --compact
```

Eval case authoring notes live in `backend/evals/README.md`. The Week 2 red-team compliance set is finalized for backend handoff.

Backend-only demo smoke runner:

```powershell
python backend/scripts/run_demo_smoke.py
```

This runs the pre-demo sequence in one command: backend unit tests, token-safe red-team compliance eval, and live Sonnet brand voice calibration. To skip the live Sonnet step for a token-free local check:

```powershell
python backend/scripts/run_demo_smoke.py --skip-live-brand-voice
```

Backend-only brand voice calibration runner:

```powershell
python backend/scripts/run_brand_voice_eval.py --compact
```

The brand voice runner evaluates the six-case near-miss calibration set in `backend/evals/brand_voice_calibration_cases.json` against `check_brand_voice`. This set is kept separate from the 20-case primary red-team eval to keep the headline accuracy metric defensible. Confidence threshold is hardcoded at 0.75 for Agent 2.0; calibrate against this set before demo.

It supports the same targeted run options:

```powershell
python backend/scripts/run_brand_voice_eval.py --start 1 --end 3 --compact
python backend/scripts/run_brand_voice_eval.py --case-id tower28_good_clean_fun_instagram_on_voice
```

## Agent 2.0 Response Fields

Five new fields added to every per-channel result object (all present when `generation_status` is `"completed"`; `null` when `generation_status` is `"error"`):

| Field | Type | Notes |
|---|---|---|
| `voice_status` | string | `"ON_VOICE"` \| `"DRIFTED"` |
| `voice_confidence` | float 0.0–1.0 | Below 0.75 routes to `NEEDS_HUMAN_REVIEW` |
| `voice_reason` | string or null | Always populated when Brand Voice Agent runs; specific, never generic |
| `compliance_confidence` | float 0.0–1.0 | Null if compliance never ran (voice `DRIFTED` gated it out) |
| `escalation_trigger` | string or null | `"voice"` \| `"compliance"` \| `null`; never `"both"` |

`compliance_status` now allows three values: `PASSED` | `FAILED` | `NEEDS_HUMAN_REVIEW`.

When `compliance_status` is `NEEDS_HUMAN_REVIEW` and compliance never ran (voice `DRIFTED`), `flagged_phrases`, `explanation`, `detection_source`, `final_safe_output`, `retry_exhausted`, and `compliance_confidence` are all `null`. `final_safe_output` stays `null` for any `NEEDS_HUMAN_REVIEW` result regardless of whether compliance ran.

See `BEAUTYAGENT_API_CONTRACT.md` Section 9 for the full routing table and example payloads (Examples 6 and 7).

## LLM Usage Tracking

Live `/generate`, red-team, and brand voice eval scripts report token/cost usage when LiteLLM returns usage metadata.

Each run prints:

- current-run usage by LLM call
- current-run totals
- local ledger grand totals

The default local ledger path is:

```text
backend/logs/llm_usage_local.jsonl
```

`backend/logs/` is ignored by git. Do not commit local usage ledgers. Ledger entries store metadata only: timestamp, call name, model, prompt tokens, completion tokens, total tokens, and estimated cost. They do not store prompts or model responses.

To use a temporary ledger path:

```powershell
$env:LLM_USAGE_LEDGER_PATH="C:\path\to\usage.jsonl"
```

## Tests

```powershell
python -m unittest discover -s backend\tests -v
```

Current backend checks:

```powershell
python -m unittest discover -s backend\tests -v
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
```

Full handoff smoke:

```powershell
python backend/scripts/run_demo_smoke.py
```

Live Render smoke:

```powershell
python backend/scripts/smoke_render_live.py
```

## Deployment

See `backend/DEPLOYMENT.md` for Render Blueprint, manual service settings, environment variables, and health check notes. The root `render.yaml` defines the backend web service.

Week 2 backend readiness and frontend handoff notes live in `backend/evals/WEEK2_BACKEND_READINESS.md`.

## Scope

- Brands: Tower 28 and Half Magic
- Channels: TikTok, Instagram, Email
- Compliance status: `PASSED`, `FAILED`, or `NEEDS_HUMAN_REVIEW`
- Static JSON config only
