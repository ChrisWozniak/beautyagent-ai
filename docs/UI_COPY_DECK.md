# UI Copy Deck — Content Agent Dashboard

Static copy for loading, error, empty, and result states. Written as tool UI copy (internal-facing, clear and neutral) — distinct from brand voice, which only applies to generated content itself, not the app around it.

**Cross-referenced against Week 2 backend contract updates on 2026-07-14 — revision notes:**
- Week 2 now includes three compliance statuses from the API: `PASSED`, `FAILED`, and `NEEDS_HUMAN_REVIEW`. The third state is used when brand voice or compliance confidence is below threshold.
- The input form field is **actives** (`coreActives` in the contract — active ingredients, e.g. "Hypochlorous Acid, Niacinamide"), not "activities." Fields are: brand, product, actives, brief, channels.
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

Three compliance states exist for Week 2. Use shared UI constants, not per-brand config.

| Status | Badge label | Sublabel copy |
|---|---|---|
| Passed | Compliant | On-voice, on-tone. No restricted phrases detected. |
| Failed | Needs a tweak | Flagged for review — see explanation below. |
| Needs Sign-Off | Needs Sign-Off | Needs a human check before copy can be used. |

**Generic failure reason template** (mirrors the contract's `explanation` field — plain-language, no legal jargon):
> "[flagged phrase]" — [one-line reason, e.g. "claims to treat a medical condition, which cosmetics can't legally do"]. Here's a safer rewrite:

*(Followed by `final_safe_output` and a Copy-to-clipboard button, per PRD User Journey 2.)*

---

## 5. Worked Examples — PASSED, FAILED, NEEDS_HUMAN_REVIEW, and Partial (Technical Error)

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

### NEEDS_HUMAN_REVIEW example

**Status:** Needs Sign-Off
**Generated copy:** show `raw_draft`
**System note:** use `voice_reason` when `escalation_trigger` is `"voice"`, or `explanation` when `escalation_trigger` is `"compliance"`.
**Card header subtext:**
- `escalation_trigger: "voice"` -> "Flagged by brand voice review — compliance check not yet run."
- `escalation_trigger: "compliance"` -> "Passed brand voice review. Flagged during compliance check."
**Safe rewrite:** do not show a final rewrite when `final_safe_output` is `null`.

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

- Compliance states for Week 2 are `PASSED`, `FAILED`, and `NEEDS_HUMAN_REVIEW`.
- `generation_status` and `compliance_status` are two separate axes, not one status field. Check `generation_status` first when rendering any card — a `"completed"` card shows the compliance badge; an `"error"` card shows the neutral error treatment instead and never has a compliance badge at all.
- Card order should be fixed (TikTok → Instagram → Email) regardless of selection order, per the contract's frontend notes — helps build muscle memory for returning users.
- The failure reason template pulls its "why" text from each brand's compliance rules (Half Magic and Tower 28 configs already have those written as if/then statements) — this should be close to a lookup against the agent's actual `explanation` output, not separately authored copy.
- Badge labels are a rendering concern only: the frontend maps `PASSED` to "Compliant", `FAILED` to "Needs a tweak", and `NEEDS_HUMAN_REVIEW` to "Needs Sign-Off". Never display the raw API string to the user.
