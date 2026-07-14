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
- `DECISIONS.md`

Current compatibility files may also exist at the repository root while the repo is being organized:

- `BEAUTYAGENT_API_CONTRACT.md`
- `sample_request.json`
- `sample_response.json`

No PRD file is committed to this repo. The Week 2 PRD lives outside the repository. If requirements context is unclear from `BEAUTYAGENT_API_CONTRACT.md`, `DECISIONS.md`, or this file, pause and ask rather than guessing.

Do not invent request or response fields. If the contract is unclear, pause and ask.

## Backend Scope

Build the backend for the `/generate` endpoint.

Core responsibilities:

- Accept the agreed request payload.
- Generate one result per requested channel.
- Run an independent Week 2 channel loop: generation, brand voice evaluation, conditional compliance audit, orchestration.
- Use LiteLLM for model calls. Direct Anthropic/Claude via `ANTHROPIC_API_KEY` is preferred for Week 2; OpenRouter remains a fallback provider for existing setups.
- Use Strands for the Python agent loop.
- Use tool calling with a `check_compliance` tool.
- Re-run deterministic compliance checks as a final backend safety backstop whenever compliance runs.
- Return the exact response shape defined by the API contract.

## Stack

Backend stack:

- Python
- FastAPI
- Strands
- LiteLLM
- Anthropic/Claude
- OpenRouter fallback
- Static JSON config files for rules, brands, and products

Do not add a database, auth system, scraping workflow, or persistent user storage unless explicitly requested.

## Contract Rules

Every response result object should include all contract fields.

For completed channel results:

- `generation_status` is `"completed"`
- `raw_draft` is a string
- `voice_status` is `"ON_VOICE"` or `"DRIFTED"`
- `voice_confidence` is a float from `0.0` to `1.0`
- `voice_reason` is populated whenever the Brand Voice Agent runs, regardless of verdict
- `compliance_status` is `"PASSED"`, `"FAILED"`, or `"NEEDS_HUMAN_REVIEW"`
- Jillian's UI may display these statuses as "Compliant", "Needs a tweak", and "Needs Human Review"; this is display-layer copy only, not an API contract change.
- `compliance_confidence` is a float from `0.0` to `1.0`, or `null` if compliance never ran
- `flagged_phrases` is an array when compliance runs, or `null` if compliance is skipped or the channel errors
- `explanation` is a string when compliance runs, or `null` if compliance is skipped or the channel errors. Keep repeated rule explanations deduped when multiple phrases hit the same rule.
- `detection_source` is `"deterministic"`, `"llm_audit"`, `"both"`, or `null`
- `final_safe_output` is a string only when the backend is confident enough to return copy. It is `null` for `NEEDS_HUMAN_REVIEW`.
- `retry_exhausted` is `true` only if `FAILED` after an iteration limit; otherwise `false` for clear completed compliance results and `null` for `NEEDS_HUMAN_REVIEW` or error.
- `escalation_trigger` is `"voice"`, `"compliance"`, or `null`. It is never `"both"`.
- `error` is `null`

For per-channel errors:

- `generation_status` is `"error"`
- all inapplicable fields are `null`, including all Week 2 voice/compliance fields
- `error` is an object with `code` and `message`

Top-level `error` is reserved for pre-dispatch failures only, such as invalid input or full-batch failure before channel work begins.

Field names are exact: `brandId`, `coreActives`, `results`, `raw_draft`, `final_safe_output`, `generation_status`, `compliance_status`, `detection_source`, `retry_exhausted`, `voice_status`, `voice_confidence`, `voice_reason`, `compliance_confidence`, and `escalation_trigger`. Brand IDs are `tower_28` and `half_magic`.

## Week 2 Routing

Agent 2.0 adds a Brand Voice Agent before compliance. Use a hardcoded `0.75` threshold unless the contract changes.

Per requested channel:

1. Generate draft copy.
2. Run `check_brand_voice`.
3. If `voice_confidence < 0.75`, set:
   - `voice_status: "DRIFTED"`
   - `compliance_status: "NEEDS_HUMAN_REVIEW"`
   - `compliance_confidence: null`
   - `flagged_phrases: null`
   - `explanation: null`
   - `detection_source: null`
   - `final_safe_output: null`
   - `retry_exhausted: null`
   - `escalation_trigger: "voice"`
4. If `voice_confidence >= 0.75`, run compliance.
5. If compliance confidence is below `0.75`, set:
   - `compliance_status: "NEEDS_HUMAN_REVIEW"`
   - `final_safe_output: null`
   - `retry_exhausted: null`
   - `escalation_trigger: "compliance"`
6. If both voice and compliance are confident, return clear `PASSED` or `FAILED` with `escalation_trigger: null`.

Compliance never runs after a voice-drifted result, so `escalation_trigger` cannot be `"both"`.

Per-channel independence is a P0 requirement. A Brand Voice Agent failure, malformed response, timeout, or parsing issue on one channel must not block sibling channels. Fail safe for that channel: route to `NEEDS_HUMAN_REVIEW` with voice confidence `0.0` unless the failure should be represented as a channel-level `generation_status: "error"` under the locked contract.

## Week 2 Model Calls

Expected LLM calls per channel:

- Generation: Sonnet, always.
- Brand Voice Agent: Sonnet, always.
- Compliance LLM audit: Haiku, conditional; run only when voice confidence is at least `0.75`.

The deterministic scan inside `check_compliance` is not an LLM call. It should remain as a cheap safety backstop.

For local plumbing tests, prefer mocked model responses. Haiku or cheaper models are acceptable for integration plumbing, JSON parsing, fail-safe handling, and routing tests. Use Sonnet for any evaluation that measures brand voice accuracy, confidence calibration, reason quality, the 6-case near-miss set, the 20-case eval set, or final demo behavior.

Keep model names configurable rather than hardcoded where possible:

- `ANTHROPIC_MODEL_SONNET` for generation and `check_brand_voice`
- `ANTHROPIC_MODEL_HAIKU` for the compliance LLM audit

## Compliance Rules

Compliance is hybrid in the Week 2 contract:

- deterministic scan for known banned or risky phrases
- LLM audit for softer or contextual claim risk, only after voice passes
- deterministic re-scan of final output before returning any completed result

The deterministic backstop is required even if the agent already called the compliance tool.

If LiteLLM/provider drafting fails, deterministic fallback copy must still flow through the same compliance loop: draft audit, marketer brief audit, merged audit, and final deterministic backstop. Do not add a fallback path that returns copy without `check_compliance`.

Current Week 1 code has deterministic compliance only. If implementing Week 2 in phases, either add the Haiku compliance audit or explicitly document a temporary deterministic confidence default. Do not pretend a probabilistic compliance confidence exists if the backend did not compute one.

Brief-level compliance violations are intentional. A result can be `FAILED` even when `raw_draft` and `final_safe_output` look clean because the marketer brief itself included risky direction. In that case, preserve `generation_status: "completed"`, `error: null`, and explain the issue with the `Marketer brief also included risky language:` prefix.

When a brief contains channel-specific instructions, audit the channel-relevant portion for that channel rather than failing every channel from a risky instruction scoped to one channel.

When tuning generated copy, keep output card-friendly for Jillian's UI without changing API fields:

- TikTok drafts should scan as `Hook:`, `Script:`, and `CTA:` inside the single string fields. These are not separate API fields.
- Email drafts should scan as `Subject:` followed by `Body:` inside the single string fields. These are not separate API fields.
- Instagram drafts should read as polished caption copy.
- Continue auditing both the generated draft and the marketer brief so risky input language is surfaced even when the generated copy is clean.

Do not add autonomous regeneration loops for Week 2 unless the contract changes. Current backend retry behavior is deterministic safe-output replacement and re-scan, not a new LLM generation attempt. The PRD keeps autonomous re-generation loops out of scope in favor of human review/resubmit.

## Red-Team Evals

Backend eval infrastructure lives in:

- `backend/evals/red_team_cases.json`
- `backend/evals/README.md`
- `backend/scripts/run_red_team_eval.py`

Jillian / Person A owns the final expanded eval content. Backend work should keep the runner and schema stable, support both `expected_status` and `expected_by_channel`, and avoid treating seed cases as the final demo pass-rate set without content review.

Use chunked or targeted eval runs when live LLM calls are slow:

```powershell
python backend/scripts/run_red_team_eval.py --start 1 --end 5 --compact
python backend/scripts/run_red_team_eval.py --case-id risky_collagen_boost_claim --compact
```

## Backend Validation

Run these from the repository root after backend changes:

```powershell
python -m unittest discover -s backend\tests -v
python backend/scripts/run_red_team_eval.py --compact
```

Optional live LLM smoke test:

```powershell
python backend/scripts/smoke_openrouter.py
python backend/scripts/smoke_generate_live.py
```

The smoke tests should only be considered a live pass when `USE_LLM_DRAFTING=true` and either `ANTHROPIC_API_KEY` or `OPENROUTER_API_KEY` is configured in the backend environment. A skipped smoke test is acceptable for local backend-only work but should be called out before demo/deploy.

Never put Anthropic, OpenRouter, or other provider keys in React/Vite frontend files. The frontend calls FastAPI `/generate`; the backend calls the model provider.

The backend currently returns one full `/generate` response after all requested channels complete or error. There is no streaming, polling, websocket, or mid-request progress endpoint.

## MVP Boundaries

Keep the Week 2 MVP narrow:

- Brands: Tower 28 and Half Magic
- Channels: TikTok, Instagram, Email
- Compliance states: `PASSED`, `FAILED`, and `NEEDS_HUMAN_REVIEW`
- Brand voice verdict: `ON_VOICE` or `DRIFTED`
- Confidence threshold: `0.75`
- Static JSON configuration only

Do not implement:

- user accounts
- database persistence
- live scraping
- extra brands
- extra channels
- campaign management
- export/share flows
- reviewer comments, approvals, annotations, or ticket routing
- violation category/risk-level tagging
- campaign goal/tone selectors

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
