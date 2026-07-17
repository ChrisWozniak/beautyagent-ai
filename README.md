# beautyagent-ai

BeautyAgent AI project workspace.

## Agent Role

BeautyAgent AI is a beauty marketing content agent. It generates channel-specific draft copy for supported brands, runs a Brand Voice Agent to check whether the draft matches the brand voice before compliance runs, audits the copy and marketer brief for compliance risk, and returns a structured result the frontend can render. Each channel result returns one of three statuses: PASSED, FAILED, or NEEDS_HUMAN_REVIEW.

## Problem It Solves

Beauty teams need faster first drafts without losing brand fit or accidentally making risky cosmetic claims. This app helps turn a short marketing brief into TikTok, Instagram, and email copy while flagging off-voice or compliance-sensitive output before it is used.

## Tools Used

- Frontend: React/Vite dashboard owned by Jillian.
- Backend: FastAPI `/generate` endpoint owned by Christopher.
- Agent tools: draft generation, Brand Voice Agent, deterministic compliance checker, final safety backstop, red-team evals, and live smoke tests.
- LLM providers: Claude through LiteLLM when backend API keys are configured, with OpenRouter still supported as a fallback path.
- Shared contract files: `BEAUTYAGENT_API_CONTRACT.md`, `docs/`, and `shared/live-ui-samples/`.

## How to Run

Start the backend from the repository root:

```powershell
uvicorn app.main:app --reload --app-dir backend
```

Run the frontend from `frontend/`:

```powershell
npm install
npm run dev
```

Run backend checks from the repository root:

```powershell
python -m unittest discover -s backend\tests -v
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
```

## Project Structure

```text
beautyagent-ai/
|-- frontend/
|-- backend/
|   `-- app/
|       |-- tools/
|       |-- agent/
|       `-- data/
|-- shared/
|-- docs/
|-- README.md
|-- .gitignore
`-- .env.example
```

## Team

Built by two cooperating builders:

- Jillian: frontend, UI notes, and frontend use of shared mock data.
- Christopher: backend, agent logic, tools, configs, and backend response format.

GitHub file access is shared at the repository level. Both builders should be added as collaborators with the same repository role, usually Write.

See `docs/TEAM_WORKFLOW.md` for the team ownership convention.

## Backend Quick Checks

Run these from the repository root before pushing backend changes:

```powershell
python -m unittest discover -s backend\tests -v
python backend/scripts/run_red_team_eval.py --mock-brand-voice --compact
```

For timeout-friendly eval chunks:

```powershell
python backend/scripts/run_red_team_eval.py --start 1 --end 5 --mock-brand-voice --compact
python backend/scripts/run_red_team_eval.py --case-id channel_specific_risky_instruction --mock-brand-voice --compact
```

Full Week 2 backend demo smoke:

```powershell
python backend/scripts/run_demo_smoke.py
```

Use `--skip-live-brand-voice` for a token-free local check.

Brand voice calibration evals:

```powershell
python backend/scripts/run_brand_voice_eval.py --compact
python backend/scripts/run_brand_voice_eval.py --start 1 --end 3 --compact
```

Optional live LLM smoke test:

```powershell
python backend/scripts/smoke_openrouter.py
python backend/scripts/smoke_generate_live.py
```

The smoke tests only run live drafting when `USE_LLM_DRAFTING=true` and either `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` is configured in the backend environment. Otherwise they exit as skipped.
Live eval and smoke scripts print current-run token/cost usage plus local grand totals from `backend/logs/llm_usage_local.jsonl`. The `backend/logs/` directory is gitignored.

Backend work should preserve the `/generate` contract in `BEAUTYAGENT_API_CONTRACT.md` so Jillian's frontend can continue wiring against stable fields.

For mock-to-live frontend wiring, see `docs/LIVE_ENDPOINT_MAPPING.md` and the sample responses in `shared/live-ui-samples/`.

Current backend behavior notes:

- Week 2 backend is ready for Jillian's frontend testing on branch `week-2`; see `backend/evals/WEEK2_BACKEND_READINESS.md`.
- `/generate` is one request -> one full response; there is no streaming, polling, websocket, or mid-request progress endpoint.
- LLM provider failures fall back to deterministic drafting, and fallback drafts still pass through `check_compliance` plus the final deterministic safety backstop.
- TikTok `Hook` / `Script` / `CTA` and Email `Subject` / `Body` are formatted inside `raw_draft` and `final_safe_output`; they are not separate API fields.
- Brief-level compliance violations can return `FAILED` even when the visible generated draft is clean. In that case `flagged_phrases` and `explanation` point back to risky marketer brief language.

Deployment prep lives in `backend/DEPLOYMENT.md`; the repo includes `render.yaml` for a Render web service Blueprint.

## Scope

- Brands: Tower 28 and Half Magic
- Channels: TikTok, Instagram, Email
- Compliance status: PASSED, FAILED, or NEEDS_HUMAN_REVIEW
- Static JSON config only
