# Pre-Build Decisions

Locked decisions made before Day 1 build started (and one confirmed during Day 2). Recorded here so neither team member re-litigates them mid-build.

---

## 1. No disclosure tag appended to `final_safe_output`

**Decision:** `final_safe_output` contains an exact copy of `raw_draft` when `compliance_status` is `PASSED`. Neither the backend nor the frontend appends `#ad`, `#sponsored`, or any disclosure tag.

**What changed:** Early designs assumed the tool might auto-append a disclosure tag to compliant copy as a convenience. Locked as: don't. The tool's job is compliance triage, not legal sign-off — appending a tag implies a level of review the tool doesn't provide, and brands may not need one in all contexts.

**Rationale:** Adding a tag silently changes the marketer's copy without their explicit choice, and assumes a specific distribution context the tool can't know. The marketer decides whether a disclosure is needed for their campaign; the tool flags problematic claims, not publishing decisions.

---

## 2. All response fields always present — `null` instead of omitted

**Decision:** Every field in a channel result object is always present in the API response, regardless of `generation_status`. Fields that don't apply to a given state are `null`, never omitted from the object.

**What changed:** An earlier draft of the contract omitted fields like `flagged_phrases` and `final_safe_output` when they didn't apply (e.g., on an error result). Locked as: every field always present, `null` when inapplicable.

**Rationale:** Omitting fields makes frontend rendering unpredictable — code has to handle both "field exists and is null" and "field doesn't exist," which leads to defensive `?.` chains everywhere and makes it easy to miss a case. A consistent shape means the frontend only needs to check `generation_status` first, then read the rest of the object normally.

---

## 3. Backend cap on brief length

**Decision:** 1000 characters (hard cap). Confirmed against Chris's backend validation: 1000 passes, 1001 rejects.

**What changed:** Previously estimated as "800–1000 characters, to start" — a placeholder range, not a confirmed number. Now a locked, backend-confirmed hard cap as of Chris's Day 2 backend work, replacing the earlier "800–1000, to start" placeholder.

**Rationale:** Sized for rambling/dictation-style input — a typical 4–5 sentence brief comfortably fits under 1000 characters. Short enough to keep generation fast and prompts focused; generous enough that a marketer thinking out loud doesn't hit the wall mid-sentence.

---

## 4. Add multi-channel partial-failure example to the API contract

**Decision:** Add Example 5 (multi-channel partial failure) to `BEAUTYAGENT_API_CONTRACT.md` — for all three channels (tiktok, instagram, email) showing one channel completed + PASSED, one completed + FAILED, and one error, all in one response.

**What changed:** `api_contract.md` now has 5 example payloads instead of 4.

**Rationale:** None of the original four payloads exercised more than one channel per request, so the partial-results dashboard was only ever discussed in the abstract. A real example gives Chris something concrete to build the concurrent per-channel loop against, and gives the frontend a real case to test the partial-results card layout before Day 3.

---

## 5. Channel drafting approach

**Decision:** Option B — independent draft → audit → revise loop per channel, run concurrently rather than sequentially.

**What changed:** This was previously framed as a recommendation in `api_contract.md`'s Backend Notes, not a locked decision. Now confirmed and stated as decided.

**Rationale:** The response schema already assumes this structure — each result object carries its own `retry_exhausted` and `detection_source`, which only makes sense if channels can pass, fail, and retry independently. Running the three loops concurrently (rather than sequentially) is also likely necessary to hit the PRD's `<3s` response-time target.

---

## 6. brandId values use snake_case with underscores

**Decision:** `brandId` values are `"tower_28"` and `"half_magic"` — not `"tower28"`/`"halfmagic"` as in the original locked contract.

**What changed:** The original contract locked `brandId` as `"tower28"` | `"halfmagic"`. Renamed to `"tower_28"` | `"half_magic"` and propagated across `BEAUTYAGENT_API_CONTRACT.md`, `CLAUDE.md`, and `docs/TEAM_WORKFLOW.md`.

**Rationale:** Snake_case is more readable for a two-word value than mashing the words together with no separator. Confirmed safe to change before renaming — nothing in the codebase depended on the original no-underscore values yet, so the switching cost was zero.

---

## 7. Brand and product configs stay as single combined files, not split per brand

**Decision:** `brand_configs.json` and `product_configs.json` each remain one file covering both brands, keyed internally by `brandId` — not split into `tower_28.json`/`half_magic.json` per type.

**What changed:** Considered splitting to mirror how brand-specific human-facing docs were split per brand; decided against it for the machine-facing config files.

**Rationale:** Consistency with `compliance_rules.json`, which is already one shared, brand-agnostic file — splitting brand/product configs while compliance stays single-file would create an inconsistent pattern in the same data directory for no functional gain. Confirmed via repo-wide grep that nothing depended on the existing single-file shape (only two non-functional references, both in a directory diagram in `CODEX.md`). At a fixed 2-brand POC scope, one file keyed by `brandId` is also easier to eyeball side-by-side and needs only one `json.load()` + dict lookup on the backend.

---

## 8. `coreActives` is omitted from the request when empty, not sent as `""` or `null`

**Decision:** The frontend omits the `coreActives` key entirely from the `/generate` request body when the field is left blank.

**What changed:** Contract marked `coreActives` optional but never specified the shape when empty. Confirmed via the contract-vs-implementation audit that the backend's request validator handles this correctly (normalizes `""` to `None`, and accepts the key being absent entirely).

**Rationale:** Decision #2 (fields always present, null when inapplicable) is explicitly scoped to response fields, not requests — there's no existing precedent requiring the same treatment on the request side. Omitting a genuinely-not-provided optional field is the more natural request convention, and the backend already handles it gracefully.

---

## 9. Form channel order now matches results dashboard order (TikTok → Instagram → Email)

**Decision:** Channel chips on the input form are ordered TikTok → Instagram → Email, matching the results dashboard. Previously the form used Instagram → TikTok → Email while the dashboard used TikTok → Instagram → Email.

**What changed:** Form chip order updated to align with the dashboard's existing fixed order.

**Rationale:** The mismatch was a frontend-only accident of the two components being spec'd separately, not a deliberate UX choice. There's no reason for a marketer to select channels in one order and see results come back in a different order — aligning removes unnecessary inconsistency across the app.

---

## 10. `voice_reason` populated whenever the agent runs, `null` only on error

**Decision:** `voice_reason` carries real content whenever the Brand Voice Agent actually runs — `ON_VOICE` or `DRIFTED`, doesn't matter — and is `null` only when `generation_status` is `"error"`.

**Rationale:** Matches the precedent already set by `explanation` (populated whenever compliance runs and has something to report, `null` only when it never ran). The Brand Voice Agent's prompt always generates a reason sentence regardless of verdict, so there's no "ran but had nothing to say" case here the way `explanation` has for a clean PASS.

---

## 11. Compliance-related fields `null` when compliance is skipped or unconfident

**Decision:** When `voice_status` is `DRIFTED` and compliance never runs, its fields (`compliance_confidence`, `flagged_phrases`, `explanation`, `detection_source`, `final_safe_output`, `retry_exhausted`) are all `null`. This extends to any `NEEDS_HUMAN_REVIEW` result generally — `final_safe_output` stays `null` whenever `compliance_status` is `NEEDS_HUMAN_REVIEW`, whether compliance actually ran or not, since the agent doesn't hand over a rewrite it isn't confident enough to stand behind.

**Rationale:** Same logic as Decision #2 — "never ran" and "ran but not confident enough to commit to an answer" are both treated as nothing actionable to offer, consistent with how the rest of the schema already handles inapplicable data.

---

## 12. `escalation_trigger` never resolves to `"both"` — the row is dropped

**Decision:** `escalation_trigger` only ever ends up `"voice"` or `"compliance"`. The routing table's fourth row (`voice_confidence < 0.75 AND compliance_confidence < 0.75 → "both"`) is removed.

**Rationale:** Compliance never runs once voice is `DRIFTED`, so `compliance_confidence` can never have a real value in the same branch where voice already failed — there's no draft that produces two real low numbers to compare. The row described a state the sequential architecture can't reach.

---

## 13. `error.detail` wiring folded into Week 2 Phase 3

**Decision:** Wiring the backend's `error.detail` field into the frontend's error display is done as part of Week 2 Phase 3 (not a separate follow-up task).

**Rationale:** Surfaced as a side effect of the v1 400-error fix — the generic message now shows correctly, but the specific detail still isn't surfaced. Phase 3 is already touching error/status card display for the new third state, so bundling it in is cheaper than reopening that area later.

---

## 14. Contract versioned via in-file header, filename unchanged

**Decision:** `beautyagent_api_contract.md` keeps its existing filename. A "Contract version: 2.0" line is added near the top, with the Week 2 additions living in a new Section 9.

**Rationale:** Keeps one stable, always-current path that `CLAUDE.md` and other docs already reference by exact name — avoids updating every cross-reference and renaming again for future versions.

---

## 15. Direct Anthropic API is the primary model path, not paid OpenRouter tier

**Decision:** Agent 2.0 calls Anthropic directly from the backend (FastAPI → LiteLLM → Anthropic), using `ANTHROPIC_API_KEY` (backend-only, never exposed to React/Vite). OpenRouter is retained only as a fallback path carried over from Week 1, not the default.

**What changed:** The original PRD (Dependency #3) assumed Agent 2.0's Sonnet/Haiku model assignments depended on paid OpenRouter tier access. That dependency is replaced with: a valid Anthropic API key with access to the Sonnet and Haiku models. `ANTHROPIC_MODEL_SONNET` and `ANTHROPIC_MODEL_HAIKU` env vars were also updated to drop the retired `claude-3-5-haiku-latest` model.

**Rationale:** Removes a paid-tier dependency the team doesn't control and simplifies the call path by one hop. Doesn't touch `beautyagent_api_contract.md` — this is an internal provider change, not a change to the `/generate` request/response shape — so it doesn't require the usual contract-coordination step, just a doc update so the PRD stops describing a path no longer being built.

---

## Calibration Set Evaluation Gap — [2026-07-17]

**Finding:** The 6-case brand voice calibration set in `backend/evals/brand_voice_calibration_cases.json` cannot be validated through the UI. When calibration copy samples are submitted as briefs, the generation step rewrites them into on-voice output before the voice agent evaluates — meaning the agent always evaluates its own clean draft, not the calibration sample.

**Example:** Cal-2 (Tower 28 clinical treatment copy, expected DRIFTED) returned ON_VOICE at 0.92 because the model rewrote the clinical brief into clean Tower 28 copy first.

**Resolution needed:** A `/evaluate-voice` endpoint that accepts raw copy + brandId + channel and returns a voice verdict without generation. Estimated effort: <1 hour backend work. Backlog item — not blocking demo.

**Workaround:** For DRIFTED calibration cases, rework briefs to force drifted draft output rather than using clinical/treatment language the model will silently fix.

---

## /evaluate-voice Endpoint Added — [2026-07-17]

**Decision:** Added a standalone `/evaluate-voice` endpoint to `main.py` for direct brand voice evaluation without triggering draft generation.

**Why:** The 6-case brand voice calibration set in `backend/evals/brand_voice_calibration_cases.json` could not be validated through the UI — the generation step rewrites off-brand briefs into on-voice copy before the voice agent evaluates, making DRIFTED cases untestable via normal submission flow.

**What it does:** Accepts `brandId`, `channel`, and `text` (raw copy), calls `check_brand_voice()` directly, and returns `voice_status`, `voice_confidence`, and `voice_reason` with no generation step involved.

**Scope:** ~20 lines in `main.py` only. No new files, no schema changes, no contract impact.

**Known gap:** `run_brand_voice_eval.py` still calls `check_brand_voice` directly rather than hitting the endpoint. A small HTTP adapter (~15 lines) would close this — deferred to backlog.
