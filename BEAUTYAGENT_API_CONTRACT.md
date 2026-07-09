/AI beauty agent

**AI beauty agent**

How can I help you today?

# Outputs

# Recents

****

|  |
| --- |
| AI beauty agent repo setup and claude.md configuration
        6 minutes ago |
| Pre-build frontend design preparation
        2 hours ago |
| BeautyAgent PRD comparison
        is this still in scope for binary- pass/fail? Step 3: If "FAILED," user sees the reason and sanitized rewrite, and can c...
        20 hours ago
        
        Beautyagent ai prd merged |
| AI agent for beauty brand marketing compliance
        2 days ago |

# Instructions

Add instructions to tailor Claude's responses

# Memory

Only you

Purpose & context Jillian is building a 2-person, async/remote AI agent proof-of-concept targeting a growth marketing manager at a small-to-mid-size beauty brand. The project is course/assignment-driven, with a rubric specifying four required technologies: OpenRouter (LLM gateway), Strands (Python agent SDK), LiteLLM (provider normalization layer), and tool calling via the @tool decorator. The demo deliverable requires both a red-team eval pass rate and a live walkthrough of a deployed app (Vercel frontend, Render backend). Both team members are new to building agents with Python and are working fully async and remotely as a 2-person team. Current state Architecture and stack decisions have been locked: Language: Python (required by Strands and @tool decorator) Brand test pair: Tower 28 (hardest compliance case, sensitivity-adjacent makeup claims) and Half Magic (maximalist color cosmetics, strongest tonal contrast) Channel scope: TikTok, Instagram, YouTube (core three); Blog as optional stretch Compliance architecture: Hybrid deterministic-scan + LLM-audit loop, with a safety backstop that re-runs the deterministic scan on final output regardless of agent tool-call behavior Several artifacts have been produced: beautyagentprd.md, apicontract.md, regulatorydictionary.json, brandtower28.json, and a 3-frame Figma wireframe (input form with channel selector, Strands agent technical flow with compliance scope annotations, results dashboard with per-channel COMPLIANCE: PASSED/FAILED cards). Jillian is still finalizing the PRD and is not yet ready to hand off the API contract to her partner. On the horizon Finalizing and handing off the PRD and API contract to the second team member Building out the Strands agent implementation Red-team eval pass rate testing Deploying the app to Vercel (frontend) and Render (backend) Potentially adding the Blog channel as a stretch goal Key learnings & principles Figma MCP execution: All plugin code must wrap logic in explicit try/catch blocks and return a value. Unhandled promise rejections from async errors silently roll back all node changes --- including nodes created before the error --- leaving a blank page with no error surfaced. Staged Figma commits: Building one frame per execution call, each with its own error capture, is more reliable than one large script; each stage commits independently. Viewport navigation: figma.viewport.scrollAndZoomIntoView(page.children) reliably navigates to show all created content after the final stage. Frame replacement: Existing frames can be cleanly replaced by finding them with page.children.find(n => n.name === "frame-name") and calling .remove() before recreating. Scope discipline: Jillian proactively flags scope creep risks (e.g., brand count, per-product template effort) early; this should be mirrored in architectural recommendations. UX clarity: Bare status badges (PASSED/FAILED) are ambiguous without explicit compliance-scope labeling; results UI should always contextualize what is being evaluated. Approach & patterns Prefers understanding architecture tradeoffs and pressure-testing plans before implementation or writing specs Catches scope creep early and treats it as a meaningful risk signal Iterates on UX clarity as part of technical design, not as a separate concern Works from partially-formed plans developed elsewhere and uses Claude to stress-test and restructure Tools & resources Figma MCP: File key KYTPtFyGb8pkUq3u9DnK2Y, Jillian Krebsbach's team (plan key team::1079492686407234302) Stack: OpenRouter, Strands, LiteLLM, Python @tool decorator Deployment: Vercel (frontend), Render (backend)

Last updated 21 hours ago

# Context

1% of project capacity used

  
- **BeautyAgent AI_PRD.md****

**537 lines

md

**DECISIONS.md****

**54 lines

md

**beautyagent_api_contract.md****

**446 lines

md

  
1. 

**beautyagent_api_contract.md**

**BeautyAgent AI --- ****/generate**** API Contract**

Pre-Build contract lock --- Tower 28 & Half Magic, channels: TikTok / Instagram / Email. (Blog and YouTube are out of scope this week.)

## 1. Request Schema

{

"brandId": "tower28",

"productName": "SOS Daily Rescue Facial Spray",

"coreActives": "Centella Asiatica, Niacinamide, Green Tea Extract",

"brief": "Free-text messy brief or dictation from the marketer.",

"channels": ["tiktok", "instagram", "email"]

}

## 2. Response Schema (per channel result)

{

"results": [

{

  "channel": "instagram",

  "generation_status": "completed",

  "raw_draft": "...",

  "compliance_status": "PASSED",

  "flagged_phrases": [],

  "explanation": "",

  "detection_source": null,

  "final_safe_output": "...",

  "retry_exhausted": false

}

],

"error": null

}

generation_status is the first thing to check on any result object --- it determines how to read the rest of the fields, all of which are **always present** (decided: every field always exists; inapplicable ones are null rather than omitted):

  
- **"completed"** → read raw_draft through retry_exhausted normally; error is null.
  
- **"error"** → raw_draft through retry_exhausted are all null; a per-channel error: {code, message} is populated instead.

## 3. Field Table

****

****

****

****

****

****

| Field | Req/Resp | Required | Notes |
| --- | --- | --- | --- |
| brandId | Request | yes | "tower28" |
| productName | Request | yes | Free text |
| coreActives | Request | no | Free text, comma list |
| brief | Request | yes | Free text; UX nudges ~4--5 sentences; backend cap 800--1000 characters (decided) |
| channels | Request | yes | Array of "tiktok" |
| channel | Response | always | Echoes one requested channel |
| generation_status | Response | always | "completed" |
| raw_draft | Response | always | Pre-audit draft; null if generation_status: "error" |
| compliance_status | Response | always | "PASSED" |
| flagged_phrases | Response | always | [] if PASSED; null if generation_status: "error" |
| explanation | Response | always | "" if PASSED; null if generation_status: "error" |
| detection_source | Response | always | "deterministic" |
| final_safe_output | Response | always | Safe rewrite if FAILED; exact copy of raw_draft if PASSED, no disclosure tag appended (decided); null if generation_status: "error" |
| retry_exhausted | Response | always | true only if FAILED after hitting iteration limit; null if generation_status: "error" |
| error (per-channel) | Response | always | {code, message} if generation_status: "error"; null if "completed" |
| error (top-level) | Response | always present, null on success | {code, message, detail} --- request-level failure, results is [] |

## 4. Error Handling

**Top-level errors (****results: []****) --- request never starts**

****

****

| Code | When |
| --- | --- |
| VALIDATION_ERROR | Missing/malformed request field |
| RATE_LIMITED | Whole batch rejected before any channel starts |
| INTERNAL_ERROR | Unexpected server crash before dispatch |

**Per-channel errors --- request started, one channel failed mid-flight**

****

****

| Code | When |
| --- | --- |
| TIMEOUT | That channel's generation or audit loop didn't finish in time |
| RATE_LIMITED | That specific channel's LLM call got throttled |
| TOOL_ERROR | check_compliance failed for that channel |

RATE_LIMITED can legitimately appear at either level depending on timing --- same code, different scope.

## 5. Example Payloads

**Tower 28 --- Compliance Fail**

**Request******

{

"brandId": "tower28",

"productName": "SOS Daily Rescue Facial Spray",

"coreActives": "Centella Asiatica, Niacinamide, Green Tea Extract",

"brief": "Highlight how this spray heals eczema and repairs the skin barrier overnight for redness-prone skin.",

"channels": ["instagram"]

}

**Response******

{

"results": [

{

  "channel": "instagram",

  "generation_status": "completed",

  "raw_draft": "Say goodbye to eczema and redness for good\! Our SOS Daily Rescue Facial Spray heals your skin barrier overnight, so you wake up calm, protected, and finally free of flare-ups. 🌿 \#SkinSOS",

  "compliance_status": "FAILED",

  "flagged_phrases": ["eczema", "heals your skin barrier overnight"],

  "explanation": "\\"Eczema\\" names a diagnosable skin condition --- claiming to treat it crosses into a drug claim. \\"Heals your skin barrier overnight\\" is a structure-function claim, which cosmetics can't legally make.",

  "detection_source": "both",

  "final_safe_output": "Redness-prone skin, meet your new calm-down button. SOS Daily Rescue Facial Spray helps soothe visible redness and support skin comfort, morning to night. 🌿 \#SkinSOS",

  "retry_exhausted": false

}

],

"error": null

}

**Tower 28 --- Compliance Pass**

**Request******

{

"brandId": "tower28",

"productName": "SOS Daily Rescue Facial Spray",

"coreActives": "Centella Asiatica, Niacinamide, Green Tea Extract",

"brief": "Introduce the spray as a calming, protective mist for sensitive, redness-prone skin --- no medical claims, just reassurance.",

"channels": ["email"]

}

**Response******

{

"results": [

{

  "channel": "email",

  "generation_status": "completed",

  "raw_draft": "Redness had a rough day? SOS is here to help 🌿",

  "compliance_status": "PASSED",

  "flagged_phrases": [],

  "explanation": "",

  "detection_source": null,

  "final_safe_output": "Redness had a rough day? SOS is here to help 🌿",

  "retry_exhausted": false

}

],

"error": null

}

**Half Magic --- Compliance Pass**

**Request******

{

"brandId": "halfmagic",

"productName": "Magic Drip Glitter Lipgloss",

"coreActives": "Vitamin E, Jojoba Oil",

"brief": "Fun, glittery, maximalist lipgloss --- promote the sparkle payoff and long-wear shine for a night-out look.",

"channels": ["tiktok"]

}

**Response******

{

"results": [

{

  "channel": "tiktok",

  "generation_status": "completed",

  "raw_draft": "POV: you just found your last brain cell and it's covered in glitter ✨ Magic Drip Glitter Lipgloss \= maximum sparkle, zero crunch, all night shine. Swipe once, glow forever (or at least till your next lip check) 💧",

  "compliance_status": "PASSED",

  "flagged_phrases": [],

  "explanation": "",

  "detection_source": null,

  "final_safe_output": "POV: you just found your last brain cell and it's covered in glitter ✨ Magic Drip Glitter Lipgloss \= maximum sparkle, zero crunch, all night shine. Swipe once, glow forever (or at least till your next lip check) 💧",

  "retry_exhausted": false

}

],

"error": null

}

**Half Magic --- Compliance Fail**

**Request******

{

"brandId": "halfmagic",

"productName": "Magic Drip Glitter Lipgloss",

"coreActives": "Vitamin E, Jojoba Oil",

"brief": "Emphasize the cushiony, juicy finish --- feel free to say it's clinically proven to boost lip fullness and give lips a plumped-up glow.",

"channels": ["tiktok"]

}

**Response******

{

"results": [

{

  "channel": "tiktok",

  "generation_status": "completed",

  "raw_draft": "Clinically proven to boost lip fullness ✨ Magic Drip's plush cushion formula gives you a plumped-up glow that lasts all day 💧",

  "compliance_status": "FAILED",

  "flagged_phrases": ["clinically proven"],

  "explanation": "\\"Clinically proven\\" is a literal claim of substantiating trial data --- this formula (Vitamin E, Jojoba Oil, no clinical studies) has no clinical backing for a lip-fullness claim. It's an exact banned phrase, not a paraphrase.",

  "detection_source": "deterministic",

  "final_safe_output": "Cushiony, juicy, and dripping with sparkle ✨ Magic Drip's plush, non-sticky formula wraps your lips in rich, cocooning shine all day 💧",

  "retry_exhausted": false

}

],

"error": null

}

**Tower 28 --- Multi-Channel, Partial Failure**

Demonstrates all three generation_status/compliance_status combinations in one response: one channel completes and passes, one completes and fails, one never finishes generating at all.

**Request******

{

"brandId": "tower28",

"productName": "SOS Daily Rescue Facial Spray",

"coreActives": "Centella Asiatica, Niacinamide, Green Tea Extract",

"brief": "Announce the spray across all channels --- calming, protective mist for sensitive, redness-prone skin.",

"channels": ["tiktok", "instagram", "email"]

}

**Response******

{

"results": [

{

  "channel": "tiktok",

  "generation_status": "completed",

  "raw_draft": "Redness-prone skin, this one's for you 🌿 SOS Daily Rescue Facial Spray keeps you calm and protected, no matter what today throws at you.",

  "compliance_status": "PASSED",

  "flagged_phrases": [],

  "explanation": "",

  "detection_source": null,

  "final_safe_output": "Redness-prone skin, this one's for you 🌿 SOS Daily Rescue Facial Spray keeps you calm and protected, no matter what today throws at you.",

  "retry_exhausted": false,

  "error": null

},

{

  "channel": "instagram",

  "generation_status": "completed",

  "raw_draft": "Wake up to eczema-free skin every single day ✨ SOS Daily Rescue Facial Spray repairs your barrier while you sleep.",

  "compliance_status": "FAILED",

  "flagged_phrases": ["eczema-free", "repairs your barrier while you sleep"],

  "explanation": "\\"Eczema-free\\" claims to treat a diagnosable condition --- a drug claim. \\"Repairs your barrier while you sleep\\" is a structure-function claim cosmetics can't legally make.",

  "detection_source": "both",

  "final_safe_output": "Wake up to calmer, happier skin ✨ SOS Daily Rescue Facial Spray helps support your skin barrier, morning and night.",

  "retry_exhausted": false,

  "error": null

},

{

  "channel": "email",

  "generation_status": "error",

  "raw_draft": null,

  "compliance_status": null,

  "flagged_phrases": null,

  "explanation": null,

  "detection_source": null,

  "final_safe_output": null,

  "retry_exhausted": null,

  "error": { "code": "TIMEOUT", "message": "Generation timed out after retries." }

}

],

"error": null

}

Note the top-level error stays null --- the request itself succeeded; only one channel inside it failed. This is the example to use when building and testing the desktop dashboard's partial-results layout.

## 6. Frontend Notes

  
- **Card grid is responsive, not fixed-3-column.** results returns one object per requested channel --- 1, 2, or 3 --- so the layout should adapt to however many channels were selected, not assume all three every time.
  
- **Recommend fixed card order** (TikTok → Instagram → Email) regardless of the order channels were clicked in the form --- builds muscle memory for returning users. Frontend-only decision, doesn't need backend input.
  
- **Check ****generation_status**** before anything else** when rendering a card. A "completed" card shows the compliance badge (PASSED/FAILED) as designed. An "error" card should look visually distinct --- recommend neutral/gray rather than red, since "the system couldn't run" and "the audit caught a problem" are different situations and shouldn't look the same at a glance.
  
- **Brief field UX:** soft nudge only ("~4-5 sentences, we'll take care of the rest"), no hard client-side maxlength --- a marketer mid-thought shouldn't get cut off. Backend cap is **800--1000 characters** (decided); if exceeded, surface a graceful "that's a bit long, mind trimming it?" message rather than a hard block.

## 7. Backend Notes

  
- **Per-channel loops need independent error handling**, not one shared try/except around all three --- this is required by the schema itself, since one channel can be "error" while its siblings are "completed".
  
- **Decided: independent per-channel loop, run concurrently.** Each requested channel gets its own draft → audit → revise cycle, run in parallel rather than sequentially --- needed both to satisfy the per-channel result shape (each channel can pass/fail/retry independently) and to hit the PRD's <3s response-time target.
  
- **Safety backstop is unchanged**: the backend re-runs the deterministic scan on every "completed" result regardless of what the agent's own tool calls did, before setting compliance_status.
  
- **Top-level vs. per-channel error**: top-level error is reserved for pre-dispatch failures only (bad input, full-batch rate limit) --- results: [] in that case. Anything failing after generation has started belongs in that channel's own error object, with siblings still returning normally.

## 8. Open Questions

All Pre-Build open questions have been resolved --- see decisions.md for what changed and why. No open items remain blocking Day 1.
