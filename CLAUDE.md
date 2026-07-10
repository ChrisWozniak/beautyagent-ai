# CLAUDE.md — BeautyAgent AI (Frontend / Jillian)

Behavioral guidelines for Claude when working on this project. Scope: `frontend/` only. Backend is owned by Christopher, built separately with Codex against the same contract. When in doubt, re-read this file — and re-read `BEAUTYAGENT_API_CONTRACT.md` — before writing any code.

Read these companion files before starting any session:
- `BEAUTYAGENT_API_CONTRACT.md` — the `/generate` request/response schema. Source of truth. Never invent fields.
- `docs/DECISIONS.md` — 5 locked pre-build decisions with rationale
- `docs/PRD.md` — full product requirements, user journeys, UI/UX notes (section 7)
- `DESIGN_SYSTEM.md` — finalized and reconciled against the Figma Make export (2026-07-09). All color tokens, component specs, and icon decisions are locked. See section 10 below before touching it.

---

## 1. Think Before Coding

Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing anything:

- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### Project-specific rules

**The API contract is the single source of truth for data shape.** Every response field is always present on every result object — fields that don't apply are `null`, never omitted (Decision #2). Do not write code that assumes a field might be missing; write code that checks whether it's `null`.

**`generation_status` is checked before anything else.** It determines how to read the rest of the object:
- `"completed"` → render the compliance badge (PASSED/FAILED) using `compliance_status`, `flagged_phrases`, `explanation`, `final_safe_output`, etc.
- `"error"` → all compliance fields are `null`; render the per-channel `error: {code, message}` instead, styled neutrally (not red/green).

**Card grid is responsive, not fixed-3-column.** `results` returns one object per requested channel (1–3). Never hardcode a 3-column assumption.

**Fixed card order regardless of selection order:** TikTok → Instagram → Email. This is a frontend-only decision — don't wait on backend for it.

**No disclosure tag anywhere in the UI.** `final_safe_output` is an exact copy of `raw_draft` when `compliance_status` is `PASSED` (Decision #1) — don't append `#ad` or similar, and don't build UI that implies one exists.

**Ambiguity is a signal, not a default.** If a field's meaning is unclear from the contract, ask — don't silently pick an interpretation, especially around the `null`-vs-omitted convention.

---

## 2. Simplicity First

Minimum code that solves the problem. Nothing speculative.

- No features beyond what's in PRD section 3 (Requirements) at P0/P1 for the confirmed 3-day scope.
- No abstractions for single-use code.
- No "flexibility" for brands/channels beyond the 2 pilot brands (Tower 28, Half Magic) and the 3 in-scope channels (TikTok, Instagram, Email).
- No error handling for scenarios outside the documented error codes (`VALIDATION_ERROR`, `RATE_LIMITED`, `INTERNAL_ERROR` top-level; `TIMEOUT`, `RATE_LIMITED`, `TOOL_ERROR` per-channel).
- If you write 200 lines and it could be 50, rewrite it.

Ask yourself: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### Project-specific rules

**MVP scope is fixed — binary PASSED/FAILED only.** Do not implement a `NEEDS HUMAN REVIEW` state, violation category/risk-level tagging, claim libraries, campaign goal/tone selectors, or export/share summaries. These are all explicitly Backlog (PRD section 12) — not this build.

**Static config only.** Brand and product data are hand-authored static JSON. No live scraping, no persistent database, no auth/login on the frontend.

**No new visual tokens until `DESIGN_SYSTEM.md` is finalized.** If a component needs a color, spacing value, or pattern that isn't already established in this project, stop and ask rather than inventing or reusing a value from a different project.

---

## 3. Surgical Changes

Touch only what you must. Clean up only your own mess.

When editing existing code:

- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:

- Remove imports/variables/functions that your changes made unused.
- Don't remove pre-existing dead code unless asked.

The test: every changed line should trace directly to the user's request.

### Project-specific rules

**Frontend owns `frontend/`, `docs/UI_NOTES.md`, and `shared/sample_response.json` only.** Do not modify `backend/` files. If the frontend needs a backend behavior change, document the need and flag it — don't work around a contract gap by guessing at backend internals.

**`shared/sample_request.json` and `shared/sample_response.json` are shared with the backend.** Any change to these must match `BEAUTYAGENT_API_CONTRACT.md` exactly — pull directly from the contract's Example 5 (multi-channel partial failure) rather than hand-writing a new mock, since that example already exercises all three `generation_status`/`compliance_status` combinations.

---

## 4. Goal-Driven Execution

Define success criteria. Loop until verified.

Transform tasks into verifiable goals:

- "Build the results dashboard" → "Render Example 5's response correctly: one PASSED card, one FAILED card, one gray error card — then verify against the contract's field table"
- "Fix the compliance card" → "Reproduce the case where `generation_status` is `error`, confirm all compliance fields render as `null`-safe, then verify no crash"

For multi-step tasks, state a brief plan:

```
[Step] → verify: [check]
[Step] → verify: [check]
[Step] → verify: [check]
```

---

## 5. API Contract — NEVER BREAK THIS

The `/generate` contract is the highest-risk shared surface in this project. Frontend and backend are built by different people, using different tools (Claude Code vs. Codex), against this same document. A mismatch here silently breaks integration on Day 3.

### Rules

- `BEAUTYAGENT_API_CONTRACT.md` is the single source of truth for request/response shape. `docs/DECISIONS.md` records why it looks the way it does.
- Field names are exact: `brandId` (not `brand`), `coreActives` (string, not array), `results` (not `outputs`), `raw_draft` (not `draft`), `final_safe_output` (not `safe_rewrite`), `generation_status`, `compliance_status`, `detection_source`, `retry_exhausted`.
- If a UI need suggests the contract should change, stop. Document the need. Do not build against an invented shape — flag it to Jillian/Christopher first.
- Data adapts to fit the contract. The contract does not adapt to fit the frontend's convenience.

### Response field reference

| Field | Always present? | Notes |
|---|---|---|
| `channel` | yes | echoes requested channel |
| `generation_status` | yes | `"completed"` \| `"error"` — check first |
| `raw_draft` | yes | `null` if `generation_status: "error"` |
| `compliance_status` | yes | `"PASSED"` \| `"FAILED"`; `null` if error |
| `flagged_phrases` | yes | `[]` if PASSED; `null` if error |
| `explanation` | yes | `""` if PASSED; `null` if error |
| `detection_source` | yes | `"deterministic"` \| `"llm_audit"` \| `"both"` \| `null` if PASSED or error |
| `final_safe_output` | yes | exact copy of `raw_draft` if PASSED; `null` if error |
| `retry_exhausted` | yes | `true` only if FAILED after iteration limit; `null` if error |
| `error` (per-channel) | yes | `{code, message}` if error; `null` if completed |
| `error` (top-level) | yes | `null` on success; `{code, message, detail}` on request-level failure |

---

## 6. UI/UX Requirements

Per PRD section 7 and `BEAUTYAGENT_API_CONTRACT.md` section 6 (Frontend Notes).

### Hard rules

- **Error cards must look visually distinct from FAILED cards.** Recommend neutral/gray for `generation_status: "error"` — never red. "The system couldn't run" and "the audit caught a problem" are different situations and must not look the same at a glance.
- **Compliance badges always show scope, not just a bare status.** A bare "PASSED"/"FAILED" is ambiguous without labeling what was evaluated (e.g., which channel, which brand).
- **Brief field: soft nudge only.** UX copy suggests "~4–5 sentences," no hard client-side `maxlength`. Backend cap is 800–1000 characters — if exceeded, surface a graceful message ("that's a bit long, mind trimming it?"), not a hard block or silent truncation.
- **Copy-to-clipboard on the safe/final output, with toast confirmation.**
- **Onboarding tooltip explaining PASSED/FAILED** is dismissible but always re-accessible.
- **High-contrast, colorblind-accessible dashboard.** Status must never be conveyed by color alone — pair every badge with explicit text.

### Card grid

- One card per requested channel (1–3), not a fixed 3-column layout.
- Fixed order: TikTok → Instagram → Email, regardless of selection order in the form.

---

## 7. Tech Stack

| Layer | Choice |
|---|---|
| Framework | React + Vite |
| Styling | Tailwind |
| Backend contract | `/generate` endpoint (Strands → LiteLLM → OpenRouter), consumed via `frontend/src/api/` |
| Language | JavaScript/JSX (confirm with Christopher if TS is adopted repo-wide) |
| Platform | Web, responsive card grid (PRD does not require full mobile optimization for POC) |

---

## 8. Scope Reminders (POC)

**In scope:** Tower 28 and Half Magic brand selectors; TikTok/Instagram/Email channel outputs; PASSED/FAILED/error card states; flagged phrases + plain-language explanation display; safe rewrite + copy button; static disclaimer (compliance triage only, not legal approval).

**Out of scope — do not build:** additional brands, live PDP/social scraping, persistent database or auth, `NEEDS HUMAN REVIEW` state, violation category/risk tagging, export/share summary, campaign goal/tone selectors, reviewer comments/annotations, shared example library.

If asked to add anything in the out-of-scope list, flag it as a Backlog item (PRD section 12) rather than building it.

---

## 9. Reference Files

| File | Purpose |
|---|---|
| `BEAUTYAGENT_API_CONTRACT.md` | Full request/response schema, error codes, example payloads |
| `docs/DECISIONS.md` | 5 locked pre-build decisions with rationale |
| `docs/PRD.md` | Full product requirements, user journeys, success metrics |
| `shared/sample_request.json` | Mock request matching the locked contract |
| `shared/sample_response.json` | Mock response — should mirror Example 5 (multi-channel partial failure) |

---

## 10. Design System

`DESIGN_SYSTEM.md` is the canonical frontend design reference. A few things worth
knowing before touching it again:

- Colors were reconciled against the Figma Make export (`Redesign AI Workspace UI/`)
  on 2026-07-09, but not all export values were kept — `--color-charcoal-muted` is
  deliberately `#6B6B6B`, not the export's `#8A8480`, because the export's value fails
  WCAG AA contrast (3.2–3.6:1) everywhere it's used. Don't re-adopt export color
  values without checking contrast first.
- The Figma export is Tailwind 4 + TypeScript + pnpm; `frontend/` is Tailwind 3 + JS +
  npm. Use the export as a visual reference only, never direct-port its code or its
  `@theme` CSS blocks.
- Badges display "Compliant"/"Needs a tweak" — never the raw API `compliance_status`
  values ("PASSED"/"FAILED"). A third "High risk" state is Week 2 scope, see
  `ui-changes-pending-week2.md`.
- Channel icons: real Instagram/TikTok brand glyphs, not generic Camera/Music —
  Email keeps a generic Mail icon.

