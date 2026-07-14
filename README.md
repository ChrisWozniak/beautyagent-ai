# beautyagent-ai

BeautyAgent AI project workspace.

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
python backend/scripts/run_red_team_eval.py --compact
```

For timeout-friendly eval chunks:

```powershell
python backend/scripts/run_red_team_eval.py --start 1 --end 5 --compact
python backend/scripts/run_red_team_eval.py --case-id channel_specific_risky_instruction --compact
```

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

- `/generate` is one request -> one full response; there is no streaming, polling, websocket, or mid-request progress endpoint.
- LLM provider failures fall back to deterministic drafting, and fallback drafts still pass through `check_compliance` plus the final deterministic safety backstop.
- TikTok `Hook` / `Script` / `CTA` and Email `Subject` / `Body` are formatted inside `raw_draft` and `final_safe_output`; they are not separate API fields.
- Brief-level compliance violations can return `FAILED` even when the visible generated draft is clean. In that case `flagged_phrases` and `explanation` point back to risky marketer brief language.

Deployment prep lives in `backend/DEPLOYMENT.md`; the repo includes `render.yaml` for a Render web service Blueprint.
