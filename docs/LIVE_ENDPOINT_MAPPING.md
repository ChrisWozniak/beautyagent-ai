# Live Endpoint Mapping

Use this when replacing frontend mock results with the live `/generate` response.

The backend contract stays unchanged. This file only maps backend response fields into the current frontend card model in `frontend/src/App.jsx`.

Sample response payloads for each UI state live in `shared/live-ui-samples/`.

## Request

Frontend already builds the right request shape:

```js
{
  brandId: form.brand,
  productName: form.productName.trim(),
  brief: form.brief.trim(),
  channels: form.channels,
  coreActives: form.adaptiveField.trim() // omit when blank
}
```

Backend accepts `coreActives` as omitted, `null`, blank, or a non-empty string.

## Response Order

Backend returns results in the same order as requested channels. The UI can keep its fixed display order if desired:

```js
const order = { tiktok: 0, instagram: 1, email: 2 };
results.sort((a, b) => order[a.channel] - order[b.channel]);
```

## Top-Level Response

If `response.error` is not `null`, the request failed before channel work started.

Recommended UI:

- show the full-screen request error state
- do not render channel cards
- `results` should be `[]`

Common current backend top-level code:

- `VALIDATION_ERROR`

## Channel Mapping

Always check `generation_status` first.

### Error Channel

Backend:

```js
{
  channel: "email",
  generation_status: "error",
  raw_draft: null,
  compliance_status: null,
  flagged_phrases: null,
  explanation: null,
  detection_source: null,
  final_safe_output: null,
  retry_exhausted: null,
  error: { code: "TIMEOUT", message: "Generation timed out after retries." }
}
```

Frontend card model:

```js
{
  channelId: result.channel,
  channelLabel: labelFor(result.channel),
  compliance: "error",
  errorCode: result.error?.code,
  errorMessage: result.error?.message
}
```

Render this as the neutral error card, not as a failed compliance card.

### Passed Channel

Backend:

```js
{
  generation_status: "completed",
  compliance_status: "PASSED",
  flagged_phrases: [],
  explanation: "",
  raw_draft: "...",
  final_safe_output: "..."
}
```

Frontend card model:

```js
{
  channelId: result.channel,
  channelLabel: labelFor(result.channel),
  compliance: "compliant",
  checkedNote: checkedNoteFor(result.channel),
  copy: result.final_safe_output ?? result.raw_draft,
  emailSubject: parseEmail(result.final_safe_output).subject // email only
}
```

For `PASSED`, `final_safe_output` is the same as `raw_draft`.

### Failed Channel

Backend:

```js
{
  generation_status: "completed",
  compliance_status: "FAILED",
  flagged_phrases: ["..."],
  explanation: "...",
  raw_draft: "...",
  final_safe_output: "..."
}
```

Frontend card model:

```js
{
  channelId: result.channel,
  channelLabel: labelFor(result.channel),
  compliance: "tweak",
  checkedNote: checkedNoteFor(result.channel),
  copy: result.final_safe_output,
  flagged_phrases: result.flagged_phrases ?? [],
  explanation: result.explanation ?? "",
  edit: {
    originalDraft: result.raw_draft,
    note: result.explanation,
    correctedCopy: result.final_safe_output
  }
}
```

`flagged_phrases` should feed the pills Jill added.

## Brief-Level Failures

Some failed responses are caused by risky marketer brief language even when the generated visible draft is clean.

Shape:

```js
{
  generation_status: "completed",
  compliance_status: "FAILED",
  flagged_phrases: ["boosts your skin's collagen production"],
  explanation: "Marketer brief also included risky language: ...",
  raw_draft: "Hook: Swipe Serum Concealer is your quick beauty reset...",
  final_safe_output: "Hook: Swipe Serum Concealer is your quick beauty reset...",
  error: null
}
```

UI implication:

- still render the `Needs a tweak` card
- show the flagged phrase pills
- use `explanation` as the issue note
- keep the brief-level helper copy when `explanation.includes("Marketer brief")`
- it is valid for `raw_draft` and `final_safe_output` to look identical

## Channel Labels

Suggested mapping for the current UI:

```js
const CHANNEL_META = {
  tiktok: {
    label: "TikTok Script",
    checkedNote: "Checked against cosmetic claim rules for short-form video"
  },
  instagram: {
    label: "Instagram Caption",
    checkedNote: "Checked against cosmetic vs. drug claim rules"
  },
  email: {
    label: "Email",
    checkedNote: "Checked against cosmetic claim rules for email"
  }
};
```

## Email Parsing

The backend does not return separate `subject` and `body` fields. Email content is a single string in `raw_draft` / `final_safe_output`.

Current backend formatting:

```text
Subject: A fresh reset from Tower 28

Body: SOS Daily Rescue Facial Spray brings an easy beauty update...
```

Frontend can parse for display only:

```js
function parseEmail(text = "") {
  const subjectMatch = text.match(/^Subject:\s*(.*)$/im);
  const bodyMatch = text.match(/^Body:\s*([\s\S]*)$/im);
  return {
    subject: subjectMatch?.[1]?.trim() ?? "",
    body: bodyMatch?.[1]?.trim() ?? text
  };
}
```

If parsing fails, show the full string as body text.

## TikTok Formatting

The backend does not return separate `hook`, `script`, or `cta` fields. TikTok content is a single string.

Current backend formatting:

```text
Hook: ...

Script: ...

CTA: ...
```

Frontend should display it with `white-space: pre-line` and avoid depending on separate fields.

## Loading And Progress

`/generate` is one request -> one full response.

There is no:

- streaming
- polling
- websocket
- per-channel partial response

The current loading sequence should stay timer-based until the response resolves. Backend default timeouts:

- LLM provider call: `15s`
- full per-channel pipeline: `20s`

## Adapter Sketch

```js
function mapApiResult(result) {
  const meta = CHANNEL_META[result.channel];

  if (result.generation_status === "error") {
    return {
      channelId: result.channel,
      channelLabel: meta.label,
      compliance: "error",
      errorCode: result.error?.code,
      errorMessage: result.error?.message
    };
  }

  const output = result.final_safe_output ?? result.raw_draft ?? "";
  const email = result.channel === "email" ? parseEmail(output) : null;

  if (result.compliance_status === "PASSED") {
    return {
      channelId: result.channel,
      channelLabel: meta.label,
      compliance: "compliant",
      checkedNote: meta.checkedNote,
      copy: email?.body ?? output,
      emailSubject: email?.subject
    };
  }

  return {
    channelId: result.channel,
    channelLabel: meta.label,
    compliance: "tweak",
    checkedNote: meta.checkedNote,
    copy: output,
    flagged_phrases: result.flagged_phrases ?? [],
    explanation: result.explanation ?? "",
    edit: {
      originalDraft: result.raw_draft ?? "",
      note: result.explanation ?? "",
      correctedCopy: email?.body ?? output
    },
    emailSubject: email?.subject
  };
}
```

If the frontend keeps the existing `EmailCard`, pass `emailSubject` and `copy` as parsed body text for email cards.
