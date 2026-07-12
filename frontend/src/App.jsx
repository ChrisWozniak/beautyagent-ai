import { useState, useCallback, useRef, useEffect } from "react";
import { Check, Copy, Pencil, ChevronDown, Mail, RefreshCw, HelpCircle } from "lucide-react";
import clsx from "clsx";
import { generate } from "./api/generate.js";

// ─── Brand channel icons (monochrome SVGs, recolored via currentColor) ───────

function InstagramIcon({ size = 14, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
    </svg>
  );
}

function TikTokIcon({ size = 14, className }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" className={className} aria-hidden="true">
      <path d="M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z" />
    </svg>
  );
}

// ─── Static Data ──────────────────────────────────────────────────────────────

const BRANDS = [
  { id: "tower_28", name: "Tower 28", dot: "#D97C6E", subline: "Sensitive-skin safe · Sephora-clean" },
  { id: "half_magic", name: "Half Magic", dot: "#9E7BC4", subline: "Fantasy-inspired · Performance makeup" },
];

const CHANNELS = [
  { id: "instagram", label: "Instagram Caption", sub: "With hashtags", Icon: InstagramIcon },
  { id: "tiktok", label: "TikTok Script", sub: "Spoken, 30–60 sec", Icon: TikTokIcon },
  { id: "email", label: "Email", sub: "Subject + body", Icon: Mail },
];

const GENERATING_STEPS = [
  "Reading your brief",
  "Drafting copy for each channel",
  "Checking claims against category guidelines",
  "Finalizing your campaign",
];

const CHANNEL_ORDER = ["tiktok", "instagram", "email"];

const CHANNEL_CHECKED_NOTE = {
  tiktok: "Checked against cosmetic claim rules for short-form video",
  instagram: "Checked against cosmetic vs. drug claim rules",
  email: "Checked against cosmetic claim rules for email",
};

// Mock results — Example 5 from the API contract (multi-channel partial failure).
// Order is fixed: TikTok → Instagram → Email, per contract frontend notes.
// compliance maps to API's compliance_status: "compliant" = PASSED, "tweak" = FAILED.
const ALL_RESULTS = [
  {
    channelId: "tiktok",
    channelLabel: "TikTok Script",
    compliance: "compliant",
    checkedNote: "Checked against cosmetic claim rules for short-form video",
    copy: "Redness-prone skin, this one's for you 🌿 SOS Daily Rescue Facial Spray keeps you calm and protected, no matter what today throws at you.",
  },
  {
    channelId: "instagram",
    channelLabel: "Instagram Caption",
    compliance: "tweak",
    checkedNote: "Checked against cosmetic vs. drug claim rules",
    copy: "Wake up to calmer, happier skin ✨ SOS Daily Rescue Facial Spray helps support your skin barrier, morning and night.",
    edit: {
      originalDraft:
        "Wake up to eczema-free skin every single day ✨ SOS Daily Rescue Facial Spray repairs your barrier while you sleep.",
      note: '"Eczema-free" claims to treat a diagnosable condition — a drug claim. "Repairs your barrier while you sleep" is a structure-function claim cosmetics can\'t legally make.',
      correctedCopy:
        "Wake up to calmer, happier skin ✨ SOS Daily Rescue Facial Spray helps support your skin barrier, morning and night.",
    },
  },
  {
    channelId: "email",
    channelLabel: "Email",
    compliance: "error",
    errorCode: "TIMEOUT",
  },
];

// ─── Demo fallback cases ─────────────────────────────────────────────────────
// Static response payloads for live-demo recovery. Never sent as real requests.
// brand is normalized (tower_28/half_magic) for form.brand compatibility.

const DEMO_CASES = [
  {
    label: "Case 1 — PASS · Email · Tower 28",
    brand: "tower_28",
    productName: "SOS Daily Rescue Facial Spray",
    channels: ["email"],
    response: {
      results: [
        {
          channel: "email",
          generation_status: "completed",
          raw_draft: "Redness had a rough day? SOS is here to help 🌿",
          compliance_status: "PASSED",
          flagged_phrases: [],
          explanation: "",
          detection_source: null,
          final_safe_output: "Redness had a rough day? SOS is here to help 🌿",
          retry_exhausted: false,
          error: null,
        },
      ],
      error: null,
    },
  },
  {
    label: "Case 2 — PASS · TikTok · Half Magic",
    brand: "half_magic",
    productName: "Magic Drip Glitter Lipgloss",
    channels: ["tiktok"],
    response: {
      results: [
        {
          channel: "tiktok",
          generation_status: "completed",
          raw_draft: "Hook: POV: your last brain cell just found its glow-up ✨\n\nScript: Magic Drip Glitter Lipgloss = maximum sparkle, zero crunch, all night shine. Non-sticky formula, full glitter payoff — no compromises. 💧\n\nCTA: Swipe it on when your look needs a little more magic.",
          compliance_status: "PASSED",
          flagged_phrases: [],
          explanation: "",
          detection_source: null,
          final_safe_output: "Hook: POV: your last brain cell just found its glow-up ✨\n\nScript: Magic Drip Glitter Lipgloss = maximum sparkle, zero crunch, all night shine. Non-sticky formula, full glitter payoff — no compromises. 💧\n\nCTA: Swipe it on when your look needs a little more magic.",
          retry_exhausted: false,
          error: null,
        },
      ],
      error: null,
    },
  },
  {
    label: "Case 3 — FAIL · Instagram · Tower 28",
    brand: "tower_28",
    productName: "SOS Daily Rescue Facial Spray",
    channels: ["instagram"],
    response: {
      results: [
        {
          channel: "instagram",
          generation_status: "completed",
          raw_draft: "Say goodbye to eczema and redness for good! Our SOS Daily Rescue Facial Spray heals your skin barrier overnight, so you wake up calm, protected, and finally free of flare-ups. 🌿 #SkinSOS",
          compliance_status: "FAILED",
          flagged_phrases: ["eczema", "heals your skin barrier overnight"],
          explanation: "\"Eczema\" names a diagnosable skin condition — claiming to treat it crosses into a drug claim. \"Heals your skin barrier overnight\" is a structure-function claim, which cosmetics can't legally make.",
          detection_source: "both",
          final_safe_output: "Redness-prone skin, meet your new calm-down button. SOS Daily Rescue Facial Spray helps soothe visible redness and support skin comfort, morning to night. 🌿 #SkinSOS",
          retry_exhausted: false,
          error: null,
        },
      ],
      error: null,
    },
  },
  {
    label: "Case 4 — FAIL · TikTok · Half Magic",
    brand: "half_magic",
    productName: "Magic Drip Glitter Lipgloss",
    channels: ["tiktok"],
    response: {
      results: [
        {
          channel: "tiktok",
          generation_status: "completed",
          raw_draft: "Clinically proven to boost lip fullness ✨ Magic Drip's plush cushion formula gives you a plumped-up glow that lasts all day 💧",
          compliance_status: "FAILED",
          flagged_phrases: ["clinically proven"],
          explanation: "\"Clinically proven\" is a literal claim of substantiating trial data — this formula (Vitamin E, Jojoba Oil, no clinical studies) has no clinical backing for a lip-fullness claim. It's an exact banned phrase, not a paraphrase.",
          detection_source: "deterministic",
          final_safe_output: "Hook: Your lips called — they want their glow back ✨\n\nScript: Magic Drip's plush, non-sticky formula wraps your lips in rich, cocooning shine. All the sparkle, none of the crunch. 💧\n\nCTA: Swipe it on when your look needs a little more magic.",
          retry_exhausted: false,
          error: null,
        },
      ],
      error: null,
    },
  },
  {
    label: "Rate limited — request rejected before generation",
    brand: "tower_28",
    productName: "SOS Daily Rescue Facial Spray",
    channels: ["tiktok", "instagram", "email"],
    response: {
      results: [],
      error: {
        code: "RATE_LIMITED",
        message: "Too many requests. Please wait a moment and try again.",
      },
    },
  },
];

// ─── Error copy ───────────────────────────────────────────────────────────────

function getErrorCopy(code) {
  switch (code) {
    case "TIMEOUT": return "This one's taking longer than expected.";
    case "RATE_LIMITED": return "This channel hit a rate limit.";
    case "TOOL_ERROR": return "We couldn't complete the compliance check for this one.";
    default: return "Something went wrong generating this one. The others are still ready below.";
  }
}

// ─── Badge ────────────────────────────────────────────────────────────────────

function ComplianceBadge({ level }) {
  if (level === "compliant") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-[5px] rounded-[7px] text-[11px] font-semibold tracking-wide bg-[#EBF2EE] text-[var(--color-moss)] border border-[var(--color-sage)]">
        <span className="w-[5px] h-[5px] rounded-full bg-[var(--color-moss)] flex-shrink-0" />
        Compliant
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-[5px] rounded-[7px] text-[11px] font-semibold tracking-wide bg-[var(--color-terracotta-bg)] text-[var(--color-terracotta-text)] border border-[#E8C9A8]">
      <Pencil size={9} strokeWidth={2.5} className="flex-shrink-0" />
      Needs a tweak
    </span>
  );
}

// ─── Copy button ──────────────────────────────────────────────────────────────

function CopyBtn({ text, id, copiedId, onCopy, variant = "primary" }) {
  const copied = copiedId === id;
  return (
    <button
      onClick={() => onCopy(text, id)}
      className={clsx(
        "inline-flex items-center gap-1.5 text-[12px] font-semibold px-3.5 py-2 rounded-[8px] transition-all duration-150 select-none",
        variant === "primary"
          ? "bg-[#315B4C] text-[#FCFBF9] hover:bg-[#2A4E40]"
          : "border border-border text-foreground hover:bg-secondary"
      )}
    >
      {copied ? (
        <><Check size={11} strokeWidth={2.5} />Copied</>
      ) : (
        <><Copy size={11} strokeWidth={1.8} />Copy</>
      )}
    </button>
  );
}

// ─── Field label ──────────────────────────────────────────────────────────────

function FieldLabel({ children, hint }) {
  return (
    <div className="mb-2.5">
      <p className="text-[11px] font-bold text-muted-foreground uppercase tracking-[0.1em] leading-none">
        {children}
      </p>
      {hint && (
        <p className="text-[11px] text-[#6B6B6B]/60 mt-1 font-normal normal-case tracking-normal leading-snug">
          {hint}
        </p>
      )}
    </div>
  );
}

// ─── Top nav ──────────────────────────────────────────────────────────────────

function TopNav({ step, onReset }) {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-background border-b border-border">
      <div className="max-w-[680px] mx-auto px-8 h-[52px] flex items-center justify-between">
        <button onClick={onReset} className="flex items-center gap-2.5 focus:outline-none">
          <div className="w-[26px] h-[26px] rounded-[7px] bg-[#2C2C2C] flex items-center justify-center flex-shrink-0">
            <span
              className="text-[#FCFBF9] text-[13px] font-black leading-none tracking-tighter"
              style={{ fontFamily: "var(--font-heading)" }}
            >
              A
            </span>
          </div>
          <span
            className="text-[13px] font-bold text-foreground tracking-tight"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Aura Beauty Intelligence
          </span>
        </button>
        {step === "results" && (
          <button
            onClick={onReset}
            className="text-[12px] font-medium text-muted-foreground hover:text-foreground border border-border px-3.5 py-1.5 rounded-[8px] transition-colors"
          >
            New campaign
          </button>
        )}
      </div>
    </header>
  );
}

// ─── Payload builder ─────────────────────────────────────────────────────────

function buildPayload(form) {
  const payload = {
    brandId: form.brand,
    productName: form.productName.trim(),
    brief: form.brief.trim(),
    channels: form.channels,
  };
  const actives = form.adaptiveField.trim();
  if (actives) payload.coreActives = actives;
  return payload;
}

// ─── API response → card shape mapper ────────────────────────────────────────

function mapApiResults(data) {
  const labelById = Object.fromEntries(CHANNELS.map((c) => [c.id, c.label]));
  return data.results
    .map((r) => {
      const base = { channelId: r.channel, channelLabel: labelById[r.channel] ?? r.channel };
      if (r.generation_status === "error") {
        return { ...base, compliance: "error", errorCode: r.error?.code };
      }
      if (r.compliance_status === "PASSED") {
        return {
          ...base,
          compliance: "compliant",
          checkedNote: CHANNEL_CHECKED_NOTE[r.channel] ?? "",
          copy: r.final_safe_output,
        };
      }
      return {
        ...base,
        compliance: "tweak",
        checkedNote: CHANNEL_CHECKED_NOTE[r.channel] ?? "",
        flagged_phrases: r.flagged_phrases,
        explanation: r.explanation,
        edit: {
          originalDraft: r.raw_draft,
          note: r.explanation,
          correctedCopy: r.final_safe_output,
        },
      };
    })
    .sort((a, b) => CHANNEL_ORDER.indexOf(a.channelId) - CHANNEL_ORDER.indexOf(b.channelId));
}

// ─── Compliance help popover ──────────────────────────────────────────────────

function ComplianceHelpPopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    function onMouseDown(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [open]);

  return (
    <div className="inline-flex items-center" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="How compliance checks work"
        aria-expanded={open}
        className="flex items-center justify-center w-6 h-6 rounded-full hover:bg-secondary transition-colors"
      >
        <HelpCircle size={16} strokeWidth={1.8} className="text-[var(--color-charcoal-muted)]" />
      </button>

      {open && (
        <div className="absolute left-0 top-full mt-2 w-80 max-w-[calc(100vw-2rem)] bg-card border border-border rounded-[20px] shadow-[0_1px_5px_rgba(44,44,44,0.05)] z-10 p-5 space-y-4">
          <h3
            className="text-[15px] font-bold text-[var(--color-charcoal)] leading-tight"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            How compliance checks work
          </h3>
          <p className="text-[13px] text-[var(--color-charcoal)] leading-relaxed">
            Every draft gets checked before you see it. Here's what the two outcomes mean:
          </p>
          <div className="space-y-3">
            <div className="space-y-1.5">
              <ComplianceBadge level="compliant" />
              <p className="text-[13px] text-[var(--color-charcoal-muted)] leading-relaxed">
                On-voice, on-tone, nothing flagged. Ready to use as-is.
              </p>
            </div>
            <div className="space-y-1.5">
              <ComplianceBadge level="tweak" />
              <p className="text-[13px] text-[var(--color-charcoal-muted)] leading-relaxed">
                Something in the draft could cross into a medical or treatment claim. You'll see exactly what was flagged, why, and a ready-to-use safer version.
              </p>
            </div>
          </div>
          <button
            onClick={() => setOpen(false)}
            className="inline-flex items-center text-[12px] font-semibold px-3.5 py-2 rounded-[8px] border border-border text-foreground hover:bg-secondary transition-all duration-150"
          >
            Got it
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Screen 1 · Input form ────────────────────────────────────────────────────

function InputScreen({ form, setForm, onGenerate }) {
  const canGenerate =
    form.productName.trim().length > 0 &&
    form.brief.trim().length > 0 &&
    form.channels.length > 0;

  const activeBrand = BRANDS.find((b) => b.id === form.brand);

  const toggleChannel = (id) =>
    setForm((p) => ({
      ...p,
      channels: p.channels.includes(id)
        ? p.channels.filter((c) => c !== id)
        : [...p.channels, id],
    }));

  return (
    <div className="max-w-[600px] mx-auto px-6 pt-20 pb-28">
      <div className="pt-6 mb-11">
        <div className="relative flex items-center gap-2 mb-2.5">
          <h1
            className="text-[1.875rem] font-bold text-foreground tracking-tight leading-tight"
            style={{ fontFamily: "var(--font-heading)" }}
          >
            New campaign
          </h1>
          <ComplianceHelpPopover />
        </div>
        <p className="text-[13px] text-muted-foreground leading-relaxed">
          Tell us about the product and drop in your notes. We'll draft and review your copy before you see it.
        </p>
      </div>

      <div className="space-y-9">

        {/* Brand selector */}
        <div>
          <FieldLabel>Brand</FieldLabel>
          <div className="flex gap-2.5">
            {BRANDS.map((b) => (
              <button
                key={b.id}
                onClick={() => setForm((p) => ({ ...p, brand: b.id }))}
                className={clsx(
                  "flex-1 flex items-start gap-3 px-4 py-3.5 rounded-[14px] border text-left transition-all duration-200",
                  form.brand === b.id
                    ? "bg-card border-border shadow-[0_1px_6px_rgba(44,44,44,0.08)]"
                    : "bg-secondary border-transparent hover:border-border"
                )}
              >
                <span
                  className="w-2.5 h-2.5 rounded-full flex-shrink-0 mt-[3px]"
                  style={{ backgroundColor: b.dot }}
                />
                <div>
                  <p className="text-[13px] font-semibold text-foreground leading-tight">{b.name}</p>
                  <p className="text-[11px] text-muted-foreground mt-0.5 leading-tight">{b.subline}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Product name */}
        <div>
          <FieldLabel>Product name</FieldLabel>
          <input
            value={form.productName}
            onChange={(e) => setForm((p) => ({ ...p, productName: e.target.value }))}
            placeholder={activeBrand.id === "tower_28" ? "e.g. SkinTint SPF 30" : "e.g. Celestial Liner"}
            className="w-full bg-secondary border border-border rounded-[11px] px-4 py-3 text-[14px] text-foreground placeholder:text-[#6B6B6B]/50 focus:outline-none focus:ring-2 focus:ring-[#315B4C]/20 focus:border-[#315B4C]/30 transition-all"
          />
        </div>

        {/* Product type + adaptive field */}
        <div>
          <FieldLabel>Product type</FieldLabel>
          <div className="inline-flex bg-secondary rounded-[10px] p-1 mb-5 border border-border">
            {["skincare", "makeup"].map((type) => (
              <button
                key={type}
                onClick={() => setForm((p) => ({ ...p, productType: type, adaptiveField: "" }))}
                className={clsx(
                  "px-5 py-2 rounded-[8px] text-[12px] font-semibold capitalize transition-all duration-150",
                  form.productType === type
                    ? "bg-card text-foreground shadow-[0_1px_3px_rgba(44,44,44,0.09)] border border-border"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {type}
              </button>
            ))}
          </div>

          <FieldLabel>
            {form.productType === "skincare" ? "Key active ingredients" : "Shade reference"}
          </FieldLabel>
          <input
            key={form.productType}
            value={form.adaptiveField}
            onChange={(e) => setForm((p) => ({ ...p, adaptiveField: e.target.value }))}
            placeholder={
              form.productType === "skincare"
                ? "e.g. Niacinamide, Squalane"
                : "e.g. shade name/number, undertone notes"
            }
            className="w-full bg-secondary border border-border rounded-[11px] px-4 py-3 text-[14px] text-foreground placeholder:text-[#6B6B6B]/50 focus:outline-none focus:ring-2 focus:ring-[#315B4C]/20 focus:border-[#315B4C]/30 transition-all"
          />
        </div>

        {/* Brief */}
        <div>
          <FieldLabel hint="Drop in anything — talking points, raw notes, a pasted deck. We'll work with it.">
            Your brief
          </FieldLabel>
          <textarea
            value={form.brief}
            onChange={(e) => setForm((p) => ({ ...p, brief: e.target.value }))}
            rows={8}
            placeholder={
              activeBrand.id === "tower_28"
                ? 'e.g. Launching SkinTint for summer. Angle: "your skin but better" — light coverage, clean, fragrance-free, SPF 30. Target: sensitive-skin girlies who are done with heavy bases. Key claims: dermatologist-tested, free of fragrance/parabens/sulfates. Tone: confident, minimalist, not clinical.'
                : "e.g. Launching Celestial Liner in three new shades for holiday. Angle: otherworldly precision, all-day wear. Key claims: smudge-proof, ophthalmologist-tested. Tone: fantasy-forward, luxe, unapologetically bold."
            }
            className="w-full bg-card border border-border rounded-[18px] px-5 py-4 text-[14px] text-foreground placeholder:text-[#6B6B6B]/40 focus:outline-none focus:ring-2 focus:ring-[#315B4C]/15 focus:border-[#315B4C]/25 transition-all resize-none leading-[1.75] shadow-[inset_0_1px_3px_rgba(44,44,44,0.04)]"
          />
          {form.brief.length > 900 && (
            <p className="mt-2 text-[12px] text-[#C4714A] leading-snug">
              That's a bit long — mind trimming it? Aim for 4–5 sentences to get the best results.
            </p>
          )}
        </div>

        {/* Channel chips */}
        <div>
          <FieldLabel>Channels</FieldLabel>
          <div className="flex flex-col gap-2">
            {CHANNELS.map((ch) => {
              const active = form.channels.includes(ch.id);
              return (
                <button
                  key={ch.id}
                  onClick={() => toggleChannel(ch.id)}
                  className={clsx(
                    "w-full flex items-center gap-3.5 px-4 py-3.5 rounded-[12px] text-left transition-all duration-150",
                    active
                      ? "bg-[rgba(199,215,206,0.35)] border border-[#C7D7CE]"
                      : "bg-[#F4F0EA] border border-[rgba(44,44,44,0.09)] hover:border-[#C7D7CE]"
                  )}
                >
                  <div
                    className={clsx(
                      "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors duration-150",
                      active ? "bg-[#315B4C]" : "border-2 border-[#C7D7CE] bg-transparent"
                    )}
                  >
                    <ch.Icon
                      size={14}
                      strokeWidth={1.8}
                      className={active ? "text-[#FCFBF9]" : "text-[#315B4C]"}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[13px] font-semibold text-foreground leading-tight">{ch.label}</p>
                    <p className="text-[11px] text-muted-foreground mt-0.5 leading-tight">{ch.sub}</p>
                  </div>
                  <div
                    className={clsx(
                      "w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 transition-all duration-150",
                      active ? "bg-[#315B4C]" : "border-2 border-[#C7D7CE]"
                    )}
                  >
                    {active && <Check size={9} strokeWidth={3} className="text-[#FCFBF9]" />}
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* CTA + disclaimer */}
        <div className="pt-1">
          <button
            onClick={onGenerate}
            disabled={!canGenerate}
            className={clsx(
              "w-full py-[15px] rounded-[11px] text-[14px] font-bold tracking-tight transition-all duration-200",
              canGenerate
                ? "bg-[#315B4C] text-[#FCFBF9] hover:bg-[#2A4E40] active:scale-[0.995]"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            )}
            style={{ fontFamily: "var(--font-heading)" }}
          >
            Generate Campaign
          </button>

          <p className="mt-4 text-[12px] text-[#6B6B6B] leading-[1.65] text-center">
            Copy is checked against FDA/MoCRA cosmetic-claim rules. This tool provides compliance triage only — not legal approval or sign-off.
          </p>
        </div>

      </div>
    </div>
  );
}

// ─── Screen 2 · Generating ────────────────────────────────────────────────────

function GeneratingScreen({ activeStep }) {
  return (
    <div className="max-w-[460px] mx-auto px-6 pt-32 pb-24 flex flex-col items-center text-center">
      <div className="mb-14">
        <h2
          className="text-[1.625rem] font-bold text-foreground mb-2.5 tracking-tight"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          Creating your campaign
        </h2>
        <p className="text-[13px] text-muted-foreground leading-relaxed">
          Sit tight — this usually takes about 20 seconds.
        </p>
      </div>

      <div className="w-full max-w-[320px] text-left">
        {GENERATING_STEPS.map((label, i) => {
          const done = activeStep > i + 1;
          const current = activeStep === i + 1;
          const pending = activeStep < i + 1;
          const isLast = i === GENERATING_STEPS.length - 1;

          return (
            <div key={i} className="flex items-start gap-4">
              <div className="flex flex-col items-center flex-shrink-0 pt-[2px]">
                <div className="relative w-5 h-5 flex items-center justify-center">
                  {done && (
                    <div className="w-5 h-5 rounded-full bg-[#315B4C] flex items-center justify-center">
                      <Check size={10} className="text-[#FCFBF9]" strokeWidth={3} />
                    </div>
                  )}
                  {current && (
                    <>
                      <span className="absolute inline-flex h-5 w-5 rounded-full bg-[#315B4C]/20 animate-ping" />
                      <span className="relative w-5 h-5 rounded-full border-2 border-[#315B4C]" />
                    </>
                  )}
                  {pending && <div className="w-5 h-5 rounded-full border-2 border-border" />}
                </div>
                {!isLast && (
                  <div
                    className={clsx(
                      "w-px flex-1 my-1.5 min-h-[28px] transition-colors duration-700",
                      done ? "bg-[#315B4C]/25" : "bg-border"
                    )}
                  />
                )}
              </div>

              <div className={clsx("flex-1", isLast ? "pb-0" : "pb-7")}>
                <p
                  className={clsx(
                    "text-[15px] leading-snug transition-colors duration-300",
                    done && "text-foreground font-medium",
                    current && "text-foreground font-semibold",
                    pending && "text-[#6B6B6B]/50 font-medium"
                  )}
                  style={{ fontFamily: "var(--font-heading)" }}
                >
                  {label}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Screen 3 · Results ───────────────────────────────────────────────────────

function ResultsScreen({ results, form, copiedId, onCopy }) {
  const activeBrand = BRANDS.find((b) => b.id === form.brand);
  const compliantCount = results.filter((r) => r.compliance === "compliant").length;
  const tweakCount = results.filter((r) => r.compliance === "tweak").length;
  const errorCount = results.filter((r) => r.compliance === "error").length;

  const parts = [];
  if (compliantCount) parts.push(`${compliantCount} ready`);
  if (tweakCount) parts.push(`${tweakCount} with a suggested edit`);
  if (errorCount) parts.push(`${errorCount} couldn't be generated`);
  const summaryLine = `${results.length} output${results.length !== 1 ? "s" : ""} · ${parts.join(" · ")}`;

  return (
    <div className="max-w-[680px] mx-auto px-6 pt-20 pb-28">
      <div className="pt-6 mb-10">
        <div className="flex items-center gap-2 mb-3">
          <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: activeBrand.dot }} />
          <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.12em]">
            {activeBrand.name}
          </span>
        </div>
        <h1
          className="text-[1.875rem] font-bold text-foreground tracking-tight leading-tight mb-2"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          {form.productName || "Campaign"}
        </h1>
        <p className="text-[13px] text-muted-foreground">{summaryLine}</p>
      </div>

      <div className="space-y-4">
        {results.map((result) => (
          <ResultCard key={result.channelId} result={result} copiedId={copiedId} onCopy={onCopy} />
        ))}
      </div>
    </div>
  );
}

function parseTikTokSections(copy) {
  const pattern = /(?:^|\n\n)(Hook|Script|CTA):\s*/g;
  const matches = [...copy.matchAll(pattern)];
  if (matches.length === 0) return null;
  return matches.map((match, i) => {
    const start = match.index + match[0].length;
    const end = matches[i + 1] ? matches[i + 1].index : copy.length;
    return { label: match[1], text: copy.slice(start, end).trim() };
  });
}

function TikTokScriptCopy({ copy }) {
  const sections = parseTikTokSections(copy);
  if (!sections) {
    return <p className="text-[14px] text-foreground leading-[1.8] whitespace-pre-line">{copy}</p>;
  }
  return (
    <div className="space-y-4">
      {sections.map(({ label, text }) => (
        <div key={label}>
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] mb-1">{label}</p>
          <p className="text-[14px] text-foreground leading-[1.8]">{text}</p>
        </div>
      ))}
    </div>
  );
}

function ResultCard({ result, copiedId, onCopy }) {
  const [open, setOpen] = useState(true);

  if (result.compliance === "error") {
    return (
      <div className="bg-card border border-border rounded-[20px] overflow-hidden shadow-[0_1px_5px_rgba(44,44,44,0.05)]">
        <div className="w-full flex items-center px-6 py-4 border-b border-border">
          <div className="flex items-center gap-3">
            <RefreshCw size={14} strokeWidth={1.8} className="text-[#6B6B6B] flex-shrink-0" />
            <span className="text-[13px] font-semibold text-foreground">{result.channelLabel}</span>
          </div>
        </div>
        <div className="px-6 py-5">
          <p className="text-[14px] text-[#6B6B6B] leading-[1.75]">
            {getErrorCopy(result.errorCode)}
          </p>
          <div className="mt-5 flex justify-end">
            <button className="inline-flex items-center gap-1.5 text-[12px] font-semibold px-3.5 py-2 rounded-[8px] border border-border text-foreground hover:bg-secondary transition-all duration-150">
              Retry this channel
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-[20px] overflow-hidden shadow-[0_1px_5px_rgba(44,44,44,0.05)]">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-6 py-4 border-b border-border hover:bg-[#F4F0EA]/30 transition-colors"
      >
        <div className="flex items-center gap-3">
          <ComplianceBadge level={result.compliance} />
          <span className="text-[13px] font-semibold text-foreground">{result.channelLabel}</span>
        </div>
        <ChevronDown
          size={16}
          strokeWidth={1.8}
          className={clsx("text-muted-foreground transition-transform duration-200", open ? "rotate-180" : "rotate-0")}
        />
      </button>

      {open && (
        <div>
          <div className="px-6 pt-4">
            <p className="text-[11px] text-muted-foreground">{result.checkedNote}</p>
          </div>

          {result.compliance === "compliant" ? (
            result.channelId === "email" && result.emailSubject != null ? (
              <EmailCard result={result} copiedId={copiedId} onCopy={onCopy} />
            ) : (
              <div className="px-6 py-5">
                {result.channelId === "tiktok"
                  ? <TikTokScriptCopy copy={result.copy} />
                  : <p className="text-[14px] text-foreground leading-[1.8] whitespace-pre-line">{result.copy}</p>
                }
                <div className="mt-5 flex justify-end">
                  <CopyBtn text={result.copy} id={`${result.channelId}-copy`} copiedId={copiedId} onCopy={onCopy} />
                </div>
              </div>
            )
          ) : (
            <div className="px-6 py-5 space-y-5">
              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] mb-2">
                  Original draft
                </p>
                <p className="text-[13px] text-muted-foreground leading-[1.75] whitespace-pre-line">
                  {result.edit?.originalDraft}
                </p>
              </div>

              {result.flagged_phrases?.length > 0 && (
                <div>
                  <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] mb-2">
                    Flagged phrases
                  </p>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {result.flagged_phrases.map((phrase) => (
                      <span
                        key={phrase}
                        className="px-3 py-1 rounded-full text-[12px] bg-[var(--color-terracotta-bg)] text-[var(--color-terracotta-text)]"
                      >
                        {phrase}
                      </span>
                    ))}
                  </div>
                  {result.explanation?.toLowerCase().includes('brief') && (
                    <p className="text-[13px] text-muted-foreground mt-2">
                      Note: some of this was flagged from your original brief, not the generated copy below — the draft itself may already look clean.
                    </p>
                  )}
                </div>
              )}

              <div className="bg-[var(--color-terracotta-bg)] rounded-[13px] px-4 py-4">
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.13em] mb-1.5">
                  Here's the issue
                </p>
                <p className="text-[13px] text-[var(--color-terracotta-text)] leading-[1.7]">{result.edit?.note}</p>
              </div>

              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] mb-2">
                  Suggested copy
                </p>
                {result.channelId === "tiktok"
                  ? <TikTokScriptCopy copy={result.edit?.correctedCopy ?? ""} />
                  : <p className="text-[14px] text-foreground leading-[1.8] whitespace-pre-line">{result.edit?.correctedCopy}</p>
                }
              </div>

              <div className="flex justify-end pt-1">
                <CopyBtn
                  text={result.edit?.correctedCopy ?? ""}
                  id={`${result.channelId}-copy`}
                  copiedId={copiedId}
                  onCopy={onCopy}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function EmailCard({ result, copiedId, onCopy }) {
  return (
    <div className="px-6 py-5 space-y-5">
      <div>
        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] mb-2">Subject line</p>
        <p className="text-[14px] text-foreground font-semibold leading-snug">{result.emailSubject}</p>
        <div className="mt-3 flex justify-end">
          <CopyBtn
            text={result.emailSubject ?? ""}
            id={`${result.channelId}-subject`}
            copiedId={copiedId}
            onCopy={onCopy}
            variant="ghost"
          />
        </div>
      </div>
      <div className="border-t border-border" />
      <div>
        <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] mb-2">Email body</p>
        <p className="text-[14px] text-foreground leading-[1.8] whitespace-pre-line">{result.copy}</p>
        <div className="mt-5 flex justify-end">
          <CopyBtn text={result.copy} id={`${result.channelId}-body`} copiedId={copiedId} onCopy={onCopy} />
        </div>
      </div>
    </div>
  );
}

// ─── Demo panel ──────────────────────────────────────────────────────────────

function DemoPanel({ onLoadCase }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="fixed bottom-4 right-4 z-50">
      {open && (
        <div className="mb-2 bg-card border border-border rounded-[16px] shadow-[0_4px_16px_rgba(44,44,44,0.12)] p-3 w-64">
          <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] px-2 mb-2">
            Demo fallback
          </p>
          <div className="space-y-0.5">
            {DEMO_CASES.map((c, i) => (
              <button
                key={i}
                onClick={() => { onLoadCase(c); setOpen(false); }}
                className="w-full text-left px-3 py-2 rounded-[8px] text-[12px] text-foreground hover:bg-secondary transition-colors"
              >
                {c.label}
              </button>
            ))}
          </div>
        </div>
      )}
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-[8px] bg-card border border-border text-[11px] font-semibold text-muted-foreground hover:text-foreground shadow-sm transition-colors"
      >
        Demo {open ? "▴" : "▾"}
      </button>
    </div>
  );
}

// ─── Root ─────────────────────────────────────────────────────────────────────

const INITIAL_FORM = {
  brand: "tower_28",
  productName: "",
  productType: "skincare",
  adaptiveField: "",
  brief: "",
  channels: ["tiktok", "instagram", "email"],
};

export default function App() {
  const [step, setStep] = useState("input");
  const [form, setForm] = useState(INITIAL_FORM);
  const [generatingStep, setGeneratingStep] = useState(0);
  const [copiedId, setCopiedId] = useState(null);
  const [apiError, setApiError] = useState(null);
  const [apiResponse, setApiResponse] = useState(null);

  const handleGenerate = useCallback(() => {
    const payload = buildPayload(form);
    console.log("[BeautyAgent] /generate payload:", payload);
    setStep("generating");
    setGeneratingStep(1); // Stage 1 active immediately

    // Stages 1→2→3 auto-advance on fixed timers calibrated to the 20s ceiling.
    // Stage 4 starts at t=18s but only completes when the response arrives.
    const stageTimers = [
      setTimeout(() => setGeneratingStep(2), 2000),
      setTimeout(() => setGeneratingStep(3), 13000),
      setTimeout(() => setGeneratingStep(4), 18000),
    ];

    function onResponse(errOrData) {
      stageTimers.forEach(clearTimeout);
      if (errOrData instanceof Error) {
        setApiError("Couldn't reach the server — check that the backend is running and try again.");
        setStep("error");
        return;
      }
      if (errOrData.error) {
        setApiError(errOrData.error.message ?? "Something went wrong — please try again.");
        setStep("error");
        return;
      }
      setApiResponse(errOrData);
      // Fast case: if response arrived before all timers fired, skips ahead.
      setGeneratingStep(5);
      setTimeout(() => setStep("results"), 400);
    }

    generate(payload).then(onResponse).catch(onResponse);
  }, [form]);

  const handleReset = useCallback(() => {
    setStep("input");
    setGeneratingStep(0);
    setForm(INITIAL_FORM);
    setApiError(null);
    setApiResponse(null);
  }, []);

  const handleLoadDemoCase = useCallback((c) => {
    setForm((prev) => ({ ...prev, brand: c.brand, productName: c.productName, channels: c.channels }));
    setApiResponse(c.response);
    setGeneratingStep(0);
    if (c.response.error) {
      setApiError(c.response.error.message);
      setStep("error");
    } else {
      setApiError(null);
      setStep("results");
    }
  }, []);

  const handleCopy = useCallback((text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const activeResults = apiResponse
    ? mapApiResults(apiResponse)
    : ALL_RESULTS.filter((r) => form.channels.includes(r.channelId));

  return (
    <div className="min-h-screen bg-background">
      <TopNav step={step} onReset={handleReset} />
      <main className="pt-[52px]">
        {step === "input" && (
          <InputScreen form={form} setForm={setForm} onGenerate={handleGenerate} />
        )}
        {step === "generating" && <GeneratingScreen activeStep={generatingStep} />}
        {step === "error" && (
          <div className="max-w-[460px] mx-auto px-6 pt-32 pb-24 flex flex-col items-center text-center gap-5">
            <p className="text-[14px] text-[var(--color-charcoal)] leading-relaxed">{apiError}</p>
            <button
              onClick={handleReset}
              className="inline-flex items-center text-[12px] font-semibold px-3.5 py-2 rounded-[8px] border border-border text-foreground hover:bg-secondary transition-all duration-150"
            >
              Try again
            </button>
          </div>
        )}
        {step === "results" && (
          <ResultsScreen
            results={activeResults}
            form={form}
            copiedId={copiedId}
            onCopy={handleCopy}
          />
        )}
      </main>
      <DemoPanel onLoadCase={handleLoadDemoCase} />
    </div>
  );
}
