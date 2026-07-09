# BeautyAgent AI — checkpoint sketch for the silent-PASSED risk
#
# Existing loop (per PRD section 8): draft -> check_compliance -> revise -> loop
# until PASSED or max_iterations, then return best attempt as FAILED.
#
# The checkpoint below adds ONE new pause point: not on every PASS, only on a
# PASS the LLM audit wasn't confident about. That requires a new signal
# (confidence) that today's binary check_compliance tool doesn't return yet.

CONFIDENCE_THRESHOLD = 0.75  # tune against eval set; not a guess to ship as-is


def run_compliance_loop(brand, product, channel, brief, max_iterations=3):
    draft = generate_copy(brand, product, channel, brief)

    for attempt in range(max_iterations):
        audit = check_compliance(draft)  # deterministic scan + LLM audit pass

        if audit.status == "FAILED":
            draft = revise_copy(draft, audit.flagged)
            continue

        # status == PASSED. This is the zone that matters: a PASSED card looks
        # identical whether the model is certain or just not-currently-caught.
        if audit.confidence < CONFIDENCE_THRESHOLD:
            decision = request_human_checkpoint(draft, audit)

            if decision == "no":
                # Not a violation (deterministic scan and audit both cleared it),
                # so it isn't FAILED. It's genuinely inconclusive -> its own
                # status, not a repurposed one. This is the NEEDS_HUMAN_REVIEW
                # state already sitting in the PRD backlog (section 12).
                return {
                    "status": "NEEDS_HUMAN_REVIEW",
                    "draft": draft,
                    "reason": audit.low_confidence_reason,
                }
            # decision == "yes" -> resume, fall through to return PASSED below.
            log_human_approved_low_confidence_pass(draft, audit)  # eval-set gold

        return {"status": "PASSED", "draft": draft}

    return {"status": "FAILED", "draft": draft, "flagged": audit.flagged}


def request_human_checkpoint(draft, audit):
    """Pause point. Loop does not advance past this until a decision comes back."""
    summary = build_checkpoint_summary(draft, audit)
    show_to_user(summary)  # renders as its own card state, not PASSED/FAILED
    return wait_for_user_input()  # blocks; only "yes" or "no" accepted


def build_checkpoint_summary(draft, audit):
    # Says exactly what's uncertain and why — not a full re-explanation of the
    # whole draft. One flagged phrase, one reason, one decision.
    return (
        f"{draft.channel} caption for {draft.brand} passed the compliance audit, "
        f"but the audit had low confidence ({audit.confidence:.2f}) on: "
        f"\"{audit.uncertain_phrase}\". "
        f"Reason: {audit.low_confidence_reason}\n\n"
        f"Approve to release as PASSED, or send back for revision?"
    )
