# Live UI Sample Payloads

These samples mirror the current `/generate` response contract and are intended for frontend mock-to-live wiring.

Use them to test card rendering without needing a live backend request.

## Files

- `all_passed.response.json` - all selected channels completed and passed compliance.
- `failed_from_draft.response.json` - generated draft contains risky language and returns a safer rewrite.
- `failed_from_brief.response.json` - generated draft is clean, but the marketer brief contained risky language.
- `partial_channel_error.response.json` - one channel completed, one channel failed compliance, one channel hit a technical timeout.

## Rendering Notes

- Check `generation_status` before `compliance_status`.
- `generation_status: "error"` renders a neutral technical-error card.
- `compliance_status: "PASSED"` maps to the frontend "Compliant" badge.
- `compliance_status: "FAILED"` maps to the frontend "Needs a tweak" badge.
- `flagged_phrases` feeds the phrase pills.
- `explanation` feeds the issue note.
- `final_safe_output` feeds the suggested copy.
- Email `Subject:` / `Body:` are formatted inside one string, not separate API fields.
