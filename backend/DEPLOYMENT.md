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
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=poolside/laguna-m.1:free
USE_LLM_DRAFTING=false
LLM_TIMEOUT_SECONDS=15
LLM_MAX_TOKENS=1000
CHANNEL_TIMEOUT_SECONDS=20
```

`OPENROUTER_API_KEY` is only required when `USE_LLM_DRAFTING=true`.
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

The smoke test exits as skipped unless `USE_LLM_DRAFTING=true` and `OPENROUTER_API_KEY` are configured.

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
