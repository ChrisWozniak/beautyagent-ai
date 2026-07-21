# Project Pause Notes

Date paused: 2026-07-20

## Current Live App

- Frontend production URL: https://beautyagent-ai.vercel.app
- Backend production URL: https://beautyagent-ai.onrender.com
- Backend health endpoint: https://beautyagent-ai.onrender.com/health
- Backend version endpoint: https://beautyagent-ai.onrender.com/version
- GitHub repository: https://github.com/ai-pursuit/beautyagent-ai

## Current Source of Truth

- Active branch: `main`
- Latest confirmed GitHub/Render commit: `1a519751a0499837306d5f550d79a86a95c5ba62`
- Render reported branch: `main`
- Render service name: `beautyagent-ai`

## Confirmed Health at Pause

- Render `/health`: `ok`
- Render `/version`: `ok`
- Vercel frontend: HTTP `200`
- Frontend title: `Aura Beauty Intelligence`
- Production frontend CORS origin was previously confirmed against Render.

## Current Architecture Snapshot

- Frontend: React, Vite, Tailwind CSS, lucide-react, clsx, hosted on Vercel.
- Backend: Python, FastAPI, Pydantic, Uvicorn, python-dotenv, LiteLLM, Strands-compatible tool wrappers, hosted on Render.
- Current primary model path: direct Anthropic API through LiteLLM when `ANTHROPIC_API_KEY` is configured.
- OpenRouter remains in the code/config as a fallback or alternate model path when Anthropic is not configured.
- Agent orchestrator: `backend/app/agent/beauty_agent.py`.
- Main orchestration function: `process_channel_loop(...)`.
- Brand voice tool: `backend/app/tools/check_brand_voice.py`.
- Deterministic compliance tool: `backend/app/tools/check_compliance.py`.
- Runtime voice profiles:
  - `backend/app/data/brand_voice_tower28.md`
  - `backend/app/data/brand_voice_halfmagic.md`

## Secrets and Spend Controls

- Do not commit API keys.
- Keep `ANTHROPIC_API_KEY` and any `OPENROUTER_API_KEY` only in Render environment variables or local ignored `.env` files.
- To reduce or pause Claude generation spend, set `USE_LLM_DRAFTING=false` in Render.
- The Brand Voice Agent can still spend Sonnet tokens when live `/generate` or `/evaluate-voice` calls are made.
- True production token/cost source of truth is Anthropic Console billing/usage. Local token usage is only stored in the ignored local ledger.

## Known Local-Only File

- `docs/CODEX_LESSONS_AND_GUARDRAILS.md` is intentionally local-only for now.
- Do not commit it unless the team decides it should become shared project guidance.

## Resume Checklist

1. Open the repo.
2. Run `git fetch origin`.
3. Run `git switch main`.
4. Run `git pull`.
5. Run `git status`.
6. Check Render: `https://beautyagent-ai.onrender.com/health`.
7. Check Render version: `https://beautyagent-ai.onrender.com/version`.
8. Check Vercel frontend: `https://beautyagent-ai.vercel.app`.
9. Before changing behavior, review `CODEX.md`, `CLAUDE.md`, `DECISIONS.md`, `BEAUTYAGENT_API_CONTRACT.md`, and this pause note.

## Safe Next Work Ideas

- Add a protected production usage endpoint or persistent usage store if Render-side token totals are needed.
- Convert local-only guardrails into an `AGENTS.md` or shared project guidance file after team review.
- Add a clear post-demo backlog for compliance LLM audit behavior, Render-side usage reporting, and any future brand voice calibration changes.
