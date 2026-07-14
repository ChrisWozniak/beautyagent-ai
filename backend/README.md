# BeautyAgent AI Backend

FastAPI backend for the BeautyAgent AI `/generate` endpoint.

This side of the project owns agent orchestration, compliance tooling, static backend config, and the response shape defined by the shared API contract.

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
`ANTHROPIC_MODEL_SONNET` is used for generation and the Week 2 Brand Voice Agent. `ANTHROPIC_MODEL_HAIKU` is reserved for the Week 2 compliance audit path.

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
Fallback drafts still run through the same compliance loop as LLM drafts: draft audit, marketer brief audit, merged audit, and final deterministic safety backstop.
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

Backend-only red-team eval runner:

```powershell
python backend/scripts/run_red_team_eval.py
```

The eval runner posts sample safe/risky cases through the FastAPI app and reports expected `PASSED`/`FAILED` outcomes. It supports both a single `expected_status` for all requested channels and an `expected_by_channel` map for mixed multi-channel cases.

For timeout-friendly chunks or targeted reruns:

```powershell
python backend/scripts/run_red_team_eval.py --start 1 --end 5 --compact
python backend/scripts/run_red_team_eval.py --case-id risky_collagen_boost_claim --compact
```

Eval case authoring notes live in `backend/evals/README.md`. Jillian / Person A owns the final expanded eval content.

Backend-only brand voice calibration runner:

```powershell
python backend/scripts/run_brand_voice_eval.py --compact
```

The brand voice runner evaluates the six-case near-miss set in `backend/evals/brand_voice_calibration_cases.json` against `check_brand_voice`. It supports the same targeted run options:

```powershell
python backend/scripts/run_brand_voice_eval.py --start 1 --end 3 --compact
python backend/scripts/run_brand_voice_eval.py --case-id tower28_good_clean_fun_instagram_on_voice
```

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
python backend/scripts/run_red_team_eval.py --compact
```

## Deployment

See `backend/DEPLOYMENT.md` for Render Blueprint, manual service settings, environment variables, and health check notes. The root `render.yaml` defines the backend web service.

## Scope

- Brands: Tower 28 and Half Magic
- Channels: TikTok, Instagram, Email
- Compliance status: PASSED, FAILED, or NEEDS_HUMAN_REVIEW for Week 2
- Static JSON config only
