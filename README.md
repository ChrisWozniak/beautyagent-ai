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
python -m unittest discover -s backend -p "test_*.py" -v
python backend/scripts/run_red_team_eval.py
```

Optional live OpenRouter smoke test:

```powershell
python backend/scripts/smoke_openrouter.py
python backend/scripts/smoke_generate_live.py
```

The smoke tests only run live drafting when `USE_LLM_DRAFTING=true` and `OPENROUTER_API_KEY` is configured. Otherwise they exit as skipped.

Backend work should preserve the `/generate` contract in `BEAUTYAGENT_API_CONTRACT.md` so Jillian's frontend can continue wiring against stable fields.
