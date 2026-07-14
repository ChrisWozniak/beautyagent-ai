# Backend Deployment Notes

## Render Blueprint

This repo includes a root-level `render.yaml` Blueprint for the backend web service.

Render service:

```text
beautyagent-ai-backend
```

Blueprint defaults:

```text
runtime: python
plan: free
buildCommand: pip install -r backend/requirements.txt
startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend
healthCheckPath: /health
```

`$PORT` is provided by Render at runtime. Do not hard-code `8000` in Render.

## Render Start Command

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend
```

## Required Environment Variables

```text
FRONTEND_ORIGINS=https://your-vercel-app.example
ANTHROPIC_API_KEY=your_claude_api_key_here
ANTHROPIC_MODEL_SONNET=anthropic/claude-sonnet-4-5
ANTHROPIC_MODEL_HAIKU=anthropic/claude-haiku-4-5-20251001
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=poolside/laguna-m.1:free
USE_LLM_DRAFTING=false
LLM_TIMEOUT_SECONDS=15
LLM_MAX_TOKENS=1000
CHANNEL_TIMEOUT_SECONDS=20
```

`ANTHROPIC_API_KEY` is the preferred Claude API key for live backend drafting when `USE_LLM_DRAFTING=true`.
`ANTHROPIC_MODEL_SONNET` is used for generation and the Week 2 Brand Voice Agent. `ANTHROPIC_MODEL_HAIKU` is reserved for the Week 2 compliance audit path.
`OPENROUTER_API_KEY` remains supported as a fallback provider for existing setups.
Never expose either provider key through the frontend; the frontend should call this backend's `/generate` route only.
`FRONTEND_ORIGINS` is required before browser-based deployed frontend calls will work.
The timeout and token values are optional. Keep `CHANNEL_TIMEOUT_SECONDS` higher than `LLM_TIMEOUT_SECONDS` so compliance checks have time to finish after drafting.
Set `FRONTEND_ORIGINS` to the deployed Vercel URL before live frontend/backend wiring. Use a comma-separated list if both preview and production origins need access.

## Manual Render Settings

If not using the Blueprint, create a Render Web Service from this GitHub repo with:

```text
Root Directory: .
Runtime: Python
Build Command: pip install -r backend/requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend
Health Check Path: /health
```

Then add the environment variables listed above.

## Pre-Deploy Checks

Run from the repository root:

```powershell
python -m unittest discover -s backend\tests -v
python backend/scripts/run_red_team_eval.py --compact
```

Optional live LLM smoke test:

```powershell
python backend/scripts/smoke_openrouter.py
```

The smoke test exits as skipped unless `USE_LLM_DRAFTING=true` and either `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` is configured.

## Health Check

```text
GET /health
```

Expected response:

```json
{"status": "ok"}
```

After deployment, verify:

```text
https://<render-service-url>/health
```

Then send Jill the backend base URL for her frontend env:

```text
VITE_API_URL=https://<render-service-url>
```

## Contract Notes

The deployed `/generate` route must keep the shared response shape stable:

- top-level `error` is always present
- one `results[]` item is returned per requested channel
- per-channel errors use `generation_status: "error"` with all inapplicable fields set to `null`
