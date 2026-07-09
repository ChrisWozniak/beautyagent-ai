
for all three channels (tiktok, instagram, email) showing one channel completed + PASSED, one completed + FAILED, and one error, all in one response.

**What changed:** api_contract.md now has 5 example payloads instead of 4.

**Rationale:** None of the original four payloads exercised more than one channel per request, so the partial-results dashboard was only ever discussed in the abstract. A real example gives Chris something concrete to build the concurrent per-channel loop against, and gives the frontend a real case to test the partial-results card layout before Day 3.

## 5. Channel drafting approach

**Decision:** Option B --- independent draft → audit → revise loop per channel, run concurrently rather than sequentially.

**What changed:** This was previously framed as a recommendation in api_contract.md's Backend Notes, not a locked decision. Now confirmed and stated as decided.

**Rationale:** The response schema already assumes this structure --- each result object carries its own retry_exhausted and detection_source, which only makes sense if channels can pass, fail, and retry independently. Running the three loops concurrently (rather than sequentially) is also likely necessary to hit the PRD's <3s response-time target.
