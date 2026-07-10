# CODEX.md - BeautyAgent AI Backend Guidance

This file guides Codex work in this repository. It is backend-focused and should be read before creating or changing backend code.

## Ownership

Christopher owns the backend build with Codex.

Primary backend areas:

- `backend/`
- `backend/app/`
- `backend/app/agent/`
- `backend/app/tools/`
- `backend/app/data/`
- `BEAUTYAGENT_API_CONTRACT.md`
- `shared/sample_request.json`
- `shared/sample_response.json`

Jillian owns the frontend build. Do not change frontend behavior unless explicitly asked.

## Source Of Truth

The API contract is the source of truth for request and response shape.

Expected location:

- `BEAUTYAGENT_API_CONTRACT.md`

Current compatibility files may also exist at the repository root while the repo is being organized:

- `BEAUTYAGENT_API_CONTRACT.md`
- `sample_request.json`
- `sample_response.json`

Do not invent request or response fields. If the contract is unclear, pause and ask.

## Backend Scope

Build the backend for the `/generate` endpoint.

Core responsibilities:

- Accept the agreed request payload.
- Generate one result per requested channel.
- Run an independent generation and compliance loop for each channel.
- Use OpenRouter through LiteLLM for model calls.
- Use Strands for the Python agent loop.
- Use tool calling with a `check_compliance` tool.
- Re-run deterministic compliance checks as a final backend safety backstop.
- Return the exact response shape defined by the API contract.

## Stack

Backend stack:

- Python
- FastAPI
- Strands
- LiteLLM
- OpenRouter
- Static JSON config files for rules, brands, and products

Do not add a database, auth system, scraping workflow, or persistent user storage unless explicitly requested.

## Contract Rules

Every response result object should include all contract fields.

For completed channel results:

- `generation_status` is `"completed"`
- `raw_draft` is a string
- `compliance_status` is `"PASSED"` or `"FAILED"`
- Jillian's UI may display these statuses as "Compliant" and "Needs a tweak"; this is display-layer copy only, not an API contract change.
- `flagged_phrases` is an array
- `explanation` is a string
- `detection_source` is `"deterministic"`, `"llm_audit"`, `"both"`, or `null`
- `final_safe_output` is a string
- `retry_exhausted` is a boolean
- `error` is `null`

For per-channel errors:

- `generation_status` is `"error"`
- inapplicable fields are `null`
- `error` is an object with `code` and `message`

Top-level `error` is reserved for pre-dispatch failures only, such as invalid input or full-batch failure before channel work begins.

## Compliance Rules

Compliance is hybrid:

- deterministic scan for known banned or risky phrases
- LLM audit for softer or contextual claim risk
- deterministic re-scan of final output before returning any completed result

The deterministic backstop is required even if the agent already called the compliance tool.

When tuning generated copy, keep output card-friendly for Jillian's UI without changing API fields:

- TikTok drafts should scan as `Hook:`, `Script:`, and `CTA:`.
- Email drafts should scan as `Subject:` followed by `Body:`.
- Instagram drafts should read as polished caption copy.
- Continue auditing both the generated draft and the marketer brief so risky input language is surfaced even when the generated copy is clean.

## Red-Team Evals

Backend eval infrastructure lives in:

- `backend/evals/red_team_cases.json`
- `backend/evals/README.md`
- `backend/scripts/run_red_team_eval.py`

Jillian / Person A owns the final expanded eval content. Backend work should keep the runner and schema stable, support both `expected_status` and `expected_by_channel`, and avoid treating seed cases as the final demo pass-rate set without content review.

## Backend Validation

Run these from the repository root after backend changes:

```powershell
python -m unittest discover -s backend -p "test_*.py" -v
python backend/scripts/run_red_team_eval.py
```

Optional live OpenRouter smoke test:

```powershell
python backend/scripts/smoke_openrouter.py
python backend/scripts/smoke_generate_live.py
```

The smoke tests should only be considered a live pass when `USE_LLM_DRAFTING=true` and `OPENROUTER_API_KEY` are configured. A skipped smoke test is acceptable for local backend-only work but should be called out before demo/deploy.

## MVP Boundaries

Keep the MVP narrow:

- Brands: Tower 28 and Half Magic
- Channels: TikTok, Instagram, Email
- Compliance status: binary `PASSED` or `FAILED`
- Static JSON configuration only

Do not implement:

- `NEEDS_HUMAN_REVIEW`
- user accounts
- database persistence
- live scraping
- extra brands
- extra channels
- campaign management
- export/share flows

## File Organization

Preferred backend scaffold:

```text
backend/
  app/
    main.py
    agent/
      __init__.py
      beauty_agent.py
      prompts.py
    tools/
      __init__.py
      check_compliance.py
    data/
      compliance_rules.json
      brand_configs.json
      product_configs.json
    models/
      __init__.py
      request_models.py
      response_models.py
  requirements.txt
  README.md
```

Shared examples:

```text
shared/
  sample_request.json
  sample_response.json
```

Docs:

```text
docs/
  API_CONTRACT.md
  DECISIONS.md
  TEAM_WORKFLOW.md
```

## Working Style

Prefer small, traceable changes.

- Read the contract before writing backend code.
- Keep request and response models aligned with sample JSON.
- Add simple tests when changing compliance logic or response shape.
- Keep frontend and backend concerns separate.
- Do not rewrite Jillian's frontend guidance unless asked.
- Mention unclear contract issues instead of guessing.
