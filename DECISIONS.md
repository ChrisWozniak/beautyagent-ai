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
