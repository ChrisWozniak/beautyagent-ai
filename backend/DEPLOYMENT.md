# Backend Deployment Notes

## Render Start Command

```text
uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir backend
```

## Required Environment Variables

```text
PORT=8000
FRONTEND_ORIGINS=https://your-vercel-app.example
USE_LLM_DRAFTING=false
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=poolside/laguna-m.1:free
LLM_TIMEOUT_SECONDS=15
LLM_MAX_TOKENS=1000
CHANNEL_TIMEOUT_SECONDS=20
```

`OPENROUTER_API_KEY` is only required when `USE_LLM_DRAFTING=true`.
The timeout and token values are optional. Keep `CHANNEL_TIMEOUT_SECONDS` higher than `LLM_TIMEOUT_SECONDS` so compliance checks have time to finish after drafting.

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
