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

To enable LiteLLM/OpenRouter drafting:

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

Backend-only OpenRouter smoke test:

```powershell
python backend/scripts/smoke_openrouter.py
```

The smoke test calls LiteLLM/OpenRouter directly and does not involve the frontend.
It exits as skipped unless `USE_LLM_DRAFTING=true` and `OPENROUTER_API_KEY` are configured.

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

See `backend/DEPLOYMENT.md` for Render start command, environment variables, and health check notes.

## Scope

- Brands: Tower 28 and Half Magic
- Channels: TikTok, Instagram, Email
- Compliance status: PASSED or FAILED
- Static JSON config only
