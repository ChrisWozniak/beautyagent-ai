# Aura Beauty Intelligence — Design System

Reference for implementing the frontend (React + Vite + Tailwind per the PRD). Aesthetic direction: Tower 28 meets Notion AI meets Vercel — modern clinical beauty. Minimal, calm, trustworthy, editorial. Premium SaaS, not enterprise compliance software, not a legal/audit tool.

---

## Brand

- **Name:** Aura Beauty Intelligence
- **Logo mark:** "A" monogram, white on a dark rounded-square tile (charcoal or moss-green fill), 8–10px radius
- **Header wordmark:** "Aura Beauty Intelligence" in Manrope, medium weight, next to the mark

---

## Color Tokens

```css
:root {
  --color-moss: #315B4C;        /* primary accent — primary buttons, active states, "Compliant" badge, selected icon fill */
  --color-ivory: #FCFBF9;       /* app background */
  --color-sand: #F4F0EA;        /* secondary surface — cards, inputs, unselected chip fill */
  --color-charcoal: #2C2C2C;    /* primary text */
  --color-charcoal-muted: #8A8480; /* secondary/caption text, sublabels, disclaimers — warm taupe, not neutral gray */
  --color-sage: #C7D7CE;        /* soft accents, dividers, secondary badge fill */
  --color-sage-transparent: rgba(199, 215, 206, 0.35); /* selected chip fill */
  --color-terracotta: #C4714A;      /* "Needs a tweak" badge fill + border accent, muted not saturated */
  --color-terracotta-bg: #F6EDDF;  /* "Needs a tweak" callout background */
  --color-terracotta-text: #9B5530; /* text-on-terracotta-bg — badge label, callout body text; darker for contrast on light fill */
  --color-berry: #7A3B4E;       /* "High risk" badge only — genuine legal exposure, still restrained */
  --color-berry-bg: #F1E2E6;   /* NOTE: the Figma Make export used #8B4A6E for berry, which skews more pink/purple than intended. Do not adopt that value — use #7A3B4E here when the high-risk state is built (Week 2, see ui-changes-pending-week2.md) */
  --color-border: rgba(44, 44, 44, 0.09); /* hairline borders */
}
```

**Rules:**
- No gradients, no glassmorphism, no saturated/bright colors.
- Moss green is the only strong accent — used sparingly (primary CTA, active/selected states, compliant badge). Everything else stays neutral.
- Never use pure alert red anywhere, even for the high-risk state.

---

## Typography

- **Headings:** Manrope (600–700 weight)
- **Body, labels, UI text:** Plus Jakarta Sans (400–500 weight)

**Scale** (approximate, adjust to Tailwind's default scale):

| Role | Size | Font | Weight | Color |
|---|---|---|---|---|
| Page title (e.g. product name on results dashboard) | 32–36px | Manrope | 700 | `--color-charcoal` |
| Section heading (e.g. "New campaign," "Creating your campaign") | 24–28px | Manrope | 700 | `--color-charcoal` |
| Field label / eyebrow text (uppercase, letter-spacing +0.02em) | 12–13px | Plus Jakarta Sans | 600 | `--color-charcoal-muted` |
| Body copy | 15–16px | Plus Jakarta Sans | 400 | `--color-charcoal` |
| Caption / disclaimer / sublabel text | 13px | Plus Jakarta Sans | 400 | `--color-charcoal-muted` |

Generous line-height (1.5–1.6) for body copy and generated captions — this is a reading-heavy product.

---

## Spacing & Layout

- **Base unit:** 4px
- **Section vertical rhythm:** minimum 32–48px between major sections on the input form and results dashboard — err toward more whitespace, not less.
- **Page max-width:** ~640–720px for the input form (single-column, focused); can go wider (~800px) for the results dashboard to accommodate cards.
- **Generous internal card/field padding:** 20–24px.

---

## Radius

| Element | Radius |
|---|---|
| Cards | 18–20px |
| Buttons | 8–12px (rounded rectangle, never a full pill) |
| Chips (channel toggles) | 12–14px |
| Badges (compliance status pills) | Fully rounded (pill) — small scale, reads as a tag not a button |
| Input fields / textareas | 10–12px |

---

## Shadows

- **Cards:** barely-there — a soft, low-opacity lift, not a drop shadow.
  ```css
  box-shadow: 0 1px 2px rgba(44,44,44,0.04), 0 2px 8px rgba(44,44,44,0.03);
  ```
- **Buttons at rest:** no shadow; a very subtle shadow increase is fine on hover.

---

## Components

### Primary Button
- Fill: `--color-moss`, text white, Plus Jakarta Sans 600
- Padding: ~14px vertical, 24px horizontal
- Radius: 10px
- Hover: slight opacity reduction (~90%) or 1px lift — no bounce, no color shift to a brighter green
- Disabled: sand fill, muted charcoal text, no border emphasis

### Secondary Button
- Fill: sand or transparent, thin border (`--color-border`), charcoal text
- Same padding/radius as primary

### Channel Toggle Chip
- **Selected:** `--color-sage-transparent` fill, icon in a filled moss circle (left), label (charcoal) + sublabel (muted), filled moss checkmark circle (right)
- **Unselected:** `--color-sand` fill, thin visible border, icon in a muted outline circle (left) — should still read as clickable, not disabled/grayed out — same label/sublabel styling, empty outline circle (right, no fill)
- Radius: 12–14px, full-width row, ~16px internal padding

### Compliance Badge
- **"Compliant":** sage/moss-tinted pill, small filled dot or checkmark, `--color-moss` text
- **"Needs a tweak":** `--color-terracotta-bg` pill, small pencil/edit icon, `--color-terracotta-text` text (use `--color-terracotta-text` not `--color-terracotta` — the darker value is required for contrast on the light fill)
- **"High risk"** (rare — genuine legal exposure only): `--color-berry-bg` pill, `--color-berry` text, still calm/restrained styling — never a hard red alert
- **Never** use the words "PASSED," "FAILED," or "VIOLATION" in any badge or label

### Callout (flagged-copy explanation, "Here's the issue")
- `--color-terracotta-bg` background, no heavy border, 12–14px radius
- Eyebrow label "HERE'S THE ISSUE" in small caps, `--color-terracotta`
- Body text in `--color-charcoal`, plain language, no legal jargon

### Disclaimer / Compliance-Triage Notice
- Not a bordered box or filled callout — render as quiet inline caption text under the primary CTA (13px, `--color-charcoal-muted`), understated in visual weight relative to the rest of the form
- Required content, every campaign: copy is checked against FDA/MoCRA cosmetic-claim rules; tool provides compliance triage only, not legal approval or sign-off
- Never reference FTC or any regulatory body outside PRD scope

### Card (results dashboard output card)
- `--color-sand`-adjacent white/ivory fill, 18–20px radius, hairline border, barely-there shadow
- Header row: compliance badge + channel label (left), expand/collapse chevron (right)
- "Copy" button: secondary/outline style, bottom-right, copy icon + label

### Error Card (per-channel technical failure — `generation_status: "error"`)
This state is never rendered by the Figma Make export — spec'd here only. It must look clearly distinct from both compliance states: "the system couldn't run" and "the audit caught a problem" are different situations and must not look the same at a glance (per API contract frontend notes and `UI_COPY_DECK.md` §2).

- **Shell:** same card geometry as the other result cards — 18–20px radius, hairline border, barely-there shadow. Only the header treatment and body content differ.
- **Color:** neutral/gray throughout. No moss, no terracotta, no berry. Never use a compliance badge on this card — the channel never reached a compliance verdict, so no badge should imply it did.
- **Header row:** `RefreshCw` icon from lucide-react (small, `--color-charcoal-muted`, no fill circle behind it) on the left where the compliance badge would normally sit, followed by the channel label in `--color-charcoal`. No expand/collapse chevron — the card body is always visible since there's nothing to collapse.
- **Body:** one line of plain-language copy from `UI_COPY_DECK.md` §2, matched to the error code:
  - `TIMEOUT` → "This one's taking longer than expected."
  - `RATE_LIMITED` → "This channel hit a rate limit."
  - `TOOL_ERROR` → "We couldn't complete the compliance check for this one."
  - Fallback (any other code) → "Something went wrong generating this one. The others are still ready below."
- **Action:** a single "Retry this channel" button — secondary/outline style, same visual weight as the Copy button, but replaces it entirely. There is no output to copy.
- **Card order:** holds its fixed position in the TikTok → Instagram → Email sequence regardless of which channel errored. An error on one channel does not reshuffle the other cards.

### Generating-State Progress List
- Plain-language steps only — never raw JSON, tool names, or terms like "iteration," "threshold," "POST"
- Completed step: filled moss checkmark circle
- Active step: outline circle with a subtle pulsing ring, no percentage bar
- Steps: "Reading your brief" → "Drafting copy for each channel" → "Checking claims against category guidelines" → "Finalizing your campaign"

---

## Icons

**Library:** `lucide-react` for all UI chrome icons. No decorative icon rows — icons only where they add real clarity.

| Purpose | Icon | Notes |
|---|---|---|
| Copy button | `Copy` (lucide) | Swaps to `Check` on copied state |
| Expand/collapse chevron | `ChevronDown` (lucide) | Rotates 180° when open |
| "Needs a tweak" badge | `Pencil` (lucide) | size 9, strokeWidth 2.5 |
| Generating step complete | `Check` (lucide) | In filled moss circle |
| Instagram channel chip | Instagram brand glyph (SVG) | Recolored to `--color-moss` / `--color-ivory` — do **not** use the official gradient mark or lucide's `Camera` placeholder |
| TikTok channel chip | TikTok brand glyph (SVG) | Recolored to `--color-moss` / `--color-ivory` — do **not** use the official dual-color mark or lucide's `Music` placeholder |
| Email channel chip | `Mail` (lucide) | Generic mail icon is appropriate — no single brand to represent |
| Error card header | `RefreshCw` (lucide) | Small, `--color-charcoal-muted`, no fill circle — sits where the compliance badge would be |

**Instagram and TikTok glyphs:** use the official monochrome SVG marks, recolored to the app's palette (moss fill on active state, charcoal/muted on inactive). The Figma Make export used `Camera` and `Music` from lucide as placeholders — these must be replaced with real brand glyphs before Day 3 demo. Source the SVGs from each platform's official brand kit; do not trace or modify the mark shape.

---

## Accessibility

- Maintain WCAG AA contrast for all text/background pairs, especially the muted caption/disclaimer text against ivory/sand backgrounds.
- Compliance states must be distinguishable without relying on color alone (icon + label text, not just badge color) — supports colorblind users per PRD UI requirements.
- All interactive elements (chips, buttons, badges-if-clickable) need visible focus states.

---

## Content Rules

Apply across all copy in the UI:

- Never use "PASSED," "FAILED," "VIOLATION," or alert/legal language.
- Compliance checks are always scoped to FDA/MoCRA cosmetic-vs-drug-claim rules — never reference FTC or other bodies not in the PRD's scope.
- Every generation flow must surface the compliance-triage-only disclaimer; it should never be dropped even when all outputs are compliant.
