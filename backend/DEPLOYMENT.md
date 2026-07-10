# Backend Deployment Notes

## Render Start Command

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend
```

## Required Environment Variables

```text
PORT=8000
FRONTEND_ORIGINS=https://your-vercel-app.example
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=poolside/laguna-m.1:free
USE_LLM_DRAFTING=false
LLM_TIMEOUT_SECONDS=15
LLM_MAX_TOKENS=1000
CHANNEL_TIMEOUT_SECONDS=20
```

`OPENROUTER_API_KEY` is only required when `USE_LLM_DRAFTING=true`.
The timeout and token values are optional. Keep `CHANNEL_TIMEOUT_SECONDS` higher than `LLM_TIMEOUT_SECONDS` so compliance checks have time to finish after drafting.
Set `FRONTEND_ORIGINS` to the deployed Vercel URL before live frontend/backend wiring. Use a comma-separated list if both preview and production origins need access.

## Pre-Deploy Checks

Run from the repository root:

```powershell
python -m unittest discover -s backend -p "test_*.py" -v
python backend/scripts/run_red_team_eval.py
```

Optional live LLM smoke test:

```powershell
python backend/scripts/smoke_openrouter.py
```

The smoke test exits as skipped unless `USE_LLM_DRAFTING=true` and `OPENROUTER_API_KEY` are configured.

## Health Check

```text
GET /health
```

Expected response:

```json
{"status": "ok"}
```

## Contract Notes

The deployed `/generate` route must keep the shared response shape stable:

- top-level `error` is always present
- one `results[]` item is returned per requested channel
- per-channel errors use `generation_status: "error"` with all inapplicable fields set to `null`
