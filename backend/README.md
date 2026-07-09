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

## Tests

```powershell
python -m unittest discover -s backend -p "test_*.py" -v
```

## Scope

- Brands: Tower 28 and Half Magic
- Channels: TikTok, Instagram, Email
- Compliance status: PASSED or FAILED
- Static JSON config only
