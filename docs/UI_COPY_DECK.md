# UI Copy Deck — Content Agent Dashboard

Static copy for loading, error, empty, and result states. Written as tool UI copy (internal-facing, clear and neutral) — distinct from brand voice, which only applies to generated content itself, not the app around it.

**Cross-referenced against `BeautyAgent AI_PRD.md` and `beautyagent_api_contract.md` on 2026-07-09 — revision notes:**
- Removed "Needs review" as a third compliance state. PRD Section 3 is explicit: "binary PASSED/FAILED status, no violation category or risk-level tagging, no NEEDS HUMAN REVIEW state." It's a named Week 2 Backlog item, not in scope for this build.
- The input form field is **actives** (`coreActives` in the contract — active ingredients, e.g. "Centella Asiatica, Niacinamide"), not "activities." Fields are: brand, product, actives, brief, channels.
- Error copy now follows the contract's two-tier model: **top-level errors** (`VALIDATION_ERROR`, `RATE_LIMITED`, `INTERNAL_ERROR` — request never starts, `results: []`) vs. **per-channel errors** (`TIMEOUT`, `RATE_LIMITED`, `TOOL_ERROR` — request started, one channel failed mid-flight, siblings display normally).
- brandId values: `tower_28` / `half_magic` (confirmed final as of naming reconciliation — do not use `tower28`/`halfmagic` or `tower_28_beauty`/`half_magic_beauty`).

---

## 1. Loading States

**Generating (primary):**
> Generating your [Brand] content…
> Checking against voice, tone, and compliance rules — this usually takes a few seconds.

**Per-channel (channels run concurrently, so these can appear together):**
> Drafting Instagram caption…
> Drafting TikTok script…
> Drafting email subject line…

**Re-running after an edit:**
> Regenerating with your changes…

---

## 2. Error States

### Top-level (request never starts — `results: []`)

**`VALIDATION_ERROR` (missing/malformed field, e.g. no brand or channel selected):**
> Something's missing or doesn't look right in this request.
> Check that you've selected a brand, product, and at least one channel, then try again.

**`RATE_LIMITED` (whole batch rejected before any channel starts):**
> We're getting a lot of requests right now.
> Wait a moment and try again.

**`INTERNAL_ERROR` (unexpected server crash before dispatch):**
> Something went wrong on our end before we could start generating.
> Try again — if it keeps happening, let your admin know. [Retry]

### Per-channel (request started — this channel failed, others display normally)

Per the contract's frontend notes: render these visually distinct from a FAILED compliance card — **neutral/gray, not red**. "The system couldn't run" and "the audit caught a problem" are different situations and shouldn't look the same at a glance.

**`TIMEOUT`:**
> This one's taking longer than expected.
> [Retry this channel]

**`RATE_LIMITED` (this channel's call got throttled):**
> This channel hit a rate limit.
> [Retry this channel]

**`TOOL_ERROR` (compliance check failed to run for this channel):**
> We couldn't complete the compliance check for this one.
> [Retry this channel]

**Generic per-channel fallback (any code not otherwise handled):**
> Something went wrong generating this one. The others are still ready below.
> [Retry this channel]

---

## 3. Empty States

**No content generated yet (first load):**
> No content generated yet.
> Fill out the brief and hit Generate to see results here.

**No results match current filters (if the dashboard supports filtering):**
> Nothing matches these filters.
> Try adjusting brand, channel, or status.

**No brand configs exist yet (system-level):**
> No brand configs found.
> Add a brand to get started.

---

## 4. Result Status — General Copy

Two states only, per PRD scope. Used on every result card regardless of brand — pull from a shared constants file, not per-brand config.

| Status | Badge label | Sublabel copy |
|---|---|---|
| Passed | Compliant | On-voice, on-tone. No restricted phrases detected. |
| Failed | Needs a tweak | Flagged for review — see explanation below. |

**Generic failure reason template** (mirrors the contract's `explanation` field — plain-language, no legal jargon):
> "[flagged phrase]" — [one-line reason, e.g. "claims to treat a medical condition, which cosmetics can't legally do"]. Here's a safer rewrite:

*(Followed by `final_safe_output` and a Copy-to-clipboard button, per PRD User Journey 2.)*

---

## 5. Worked Examples — PASSED, FAILED, and Partial (Technical Error)

Adapted directly from `beautyagent_api_contract.md` Section 5 (canonical examples) rather than invented copy — these are also usable as literal mock JSON for the dashboard build.

### PASSED example (Tower 28, Email)

**Status:** Compliant
**Brand:** Tower 28 · **Product:** SOS Daily Rescue Facial Spray
**Channel:** Email
**Generated copy:**
> Redness had a rough day? SOS is here to help 🌿

**System note:** On-voice, on-tone. No restricted phrases detected.

### FAILED example (Tower 28, Instagram)

**Status:** Needs a tweak
**Brand:** Tower 28 · **Product:** SOS Daily Rescue Facial Spray
**Channel:** Instagram
**Raw draft:**
> Say goodbye to eczema and redness for good! Our SOS Daily Rescue Facial Spray heals your skin barrier overnight, so you wake up calm, protected, and finally free of flare-ups. 🌿 #SkinSOS

**Flagged phrases:** "eczema," "heals your skin barrier overnight"
**Explanation:** "Eczema" names a diagnosable skin condition — claiming to treat it crosses into a drug claim. "Heals your skin barrier overnight" is a structure-function claim, which cosmetics can't legally make.
**Safe rewrite (`final_safe_output`):**
> Redness-prone skin, meet your new calm-down button. SOS Daily Rescue Facial Spray helps soothe visible redness and support skin comfort, morning to night. 🌿 #SkinSOS

### Partial-failure example (Tower 28, all 3 channels — the dashboard's key test case)

Per the contract: "This is the example to use when building and testing the desktop dashboard's partial-results layout." One channel PASSED, one FAILED, one hit a technical error — all in a single response.

| Channel | generation_status | compliance_status | Card treatment |
|---|---|---|---|
| TikTok | completed | PASSED | Sage/moss 'Compliant' card |
| Instagram | completed | FAILED | Terracotta 'Needs a tweak' card with explanation + rewrite |
| Email | error (`TIMEOUT`) | null | Neutral/gray error card — "This one's taking longer than expected. [Retry this channel]" |

This is the layout to build and screenshot-test before Day 3 — it's the only example that exercises all three card states at once.

---

## 6. Notes for whoever wires this up

- Only two compliance states exist for this build: PASSED / FAILED. "Needs review" was cut after cross-referencing the PRD — it's a confirmed Week 2 Backlog item (three-state status with confidence-based routing, ~5–6 hrs estimated), not part of this scope.
- `generation_status` and `compliance_status` are two separate axes, not one status field. Check `generation_status` first when rendering any card — a `"completed"` card shows the compliance badge; an `"error"` card shows the neutral error treatment instead and never has a compliance badge at all.
- Card order should be fixed (TikTok → Instagram → Email) regardless of selection order, per the contract's frontend notes — helps build muscle memory for returning users.
- The failure reason template pulls its "why" text from each brand's compliance rules (Half Magic and Tower 28 configs already have those written as if/then statements) — this should be close to a lookup against the agent's actual `explanation` output, not separately authored copy.
- `compliance_status` still returns `"PASSED"` / `"FAILED"` from the API exactly as the locked contract specifies — nothing changes at the data layer. Badge labels are a rendering concern only: the frontend maps `PASSED` → "Compliant" and `FAILED` → "Needs a tweak". Never display the raw API string to the user.
