# BeautyAgent AI Backend

FastAPI backend for the BeautyAgent AI `/generate` endpoint.

This side of the project owns agent orchestration, compliance tooling, static backend config, and the response shape defined by the shared API contract.

## Local Entry Point

```powershell
uvicorn app.main:app --reload --app-dir backend
```

## Scope

- Brands: Tower 28 and Half Magic
- Channels: TikTok, Instagram, Email
- Compliance status: PASSED or FAILED
- Static JSON config only

