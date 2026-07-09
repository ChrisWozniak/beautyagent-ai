import { useState, useCallback } from "react";
import { Check, Copy, Pencil, ChevronDown, Camera, Music, Mail, RefreshCw } from "lucide-react";
import clsx from "clsx";
import Layout from "./components/Layout.jsx";

// ─── Static Data ──────────────────────────────────────────────────────────────

const BRANDS = [
  { id: "tower_28", name: "Tower 28", dot: "#D97C6E", subline: "Sensitive-skin safe · Sephora-clean" },
  { id: "half_magic", name: "Half Magic", dot: "#9E7BC4", subline: "Fantasy-inspired · Performance makeup" },
];

const CHANNELS = [
  { id: "instagram", label: "Instagram Caption", sub: "With hashtags", Icon: Camera },
  { id: "tiktok", label: "TikTok Script", sub: "Spoken, 30–60 sec", Icon: Music },
  { id: "email", label: "Email", sub: "Subject + body", Icon: Mail },
];

const GENERATING_STEPS = [
  "Reading your brief",
  "Drafting copy for each channel",
  "Checking claims against category guidelines",
  "Finalizing your campaign",
];

// Mock results — hardcoded for visual reference only.
// compliance maps to API's compliance_status: "compliant" = PASSED, "tweak" = FAILED.
const ALL_RESULTS = [
  {
    channelId: "instagram",
    channelLabel: "Instagram Caption",
    compliance: "tweak",
    checkedNote: "Checked against cosmetic vs. drug claim rules",
    copy: "Tower 28 SkinTint SPF 30 — clean coverage with SPF 30, no fragrance, no fuss. ✨ Shop via link in bio. #Tower28 #CleanBeauty #SPF30 #SensitiveSkinApproved",
    edit: {
      originalDraft:
        "Tower 28 SkinTint SPF 30 — because great skin heals from the outside in. ✨ Clean, SPF-packed, and fragrance-free. Shop via link in bio. #Tower28 #CleanBeauty #SPF30",
      note: '"Heals from the outside in" reads as a treatment claim. Under FDA cosmetic guidelines, language implying the product repairs or heals skin crosses into drug-claim territory — an easy fix that keeps all the warmth of the copy.',
      correctedCopy:
        "Tower 28 SkinTint SPF 30 — clean coverage with SPF 30, no fragrance, no fuss. ✨ Shop via link in bio. #Tower28 #CleanBeauty #SPF30 #SensitiveSkinApproved",
    },
  },
  {
    channelId: "tiktok",
    channelLabel: "TikTok Script",
    compliance: "error",
    errorCode: "TIMEOUT",
  },
  {
    channelId: "email",
    channelLabel: "Email",
    compliance: "compliant",
    checkedNote: "Checked against FDA/MoCRA cosmetic claim rules for email marketing",
    emailSubject: "Your skin, its best self — Tower 28 SkinTint SPF 30",
    copy: "Meet your new everyday.\n\nTower 28 SkinTint SPF 30 is a clean, fragrance-free tinted moisturizer built for sensitive skin — and everyone else who just wants skin that looks good.\n\nSPF 30 broad spectrum. No parabens. No sulfates. No fragrance.\n\nFind it at Sephora and Target, or shop at tower28beauty.com.\n\nUse code [NAME] for 15% off your first order.\n\n—\nTower 28 Beauty\nSensitive-skin safe. Sephora-clean.",
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
      <span className="inline-flex items-center gap-1.5 px-2.5 py-[5px] rounded-[7px] text-[11px] font-semibold tracking-wide bg-[#EBF2EE] text-[#315B4C] border border-[#C7D7CE]">
        <span className="w-[5px] h-[5px] rounded-full bg-[#315B4C] flex-shrink-0" />
        Compliant
      </span>
    );
  }
  if (level === "tweak") {
    return (
      <span className="inline-flex items-center gap-1.5 px-2.5 py-[5px] rounded-[7px] text-[11px] font-semibold tracking-wide bg-[#F6EDDF] text-[#9B5530] border border-[#E8C9A8]">
        <Pencil size={9} strokeWidth={2.5} className="flex-shrink-0" />
        Needs a tweak
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 px-2.5 py-[5px] rounded-[7px] text-[11px] font-semibold tracking-wide bg-[#F2E8ED] text-[#7A3A5A] border border-[#D9B5C8]">
      <span className="w-[5px] h-[5px] rounded-full bg-[#7A3A5A] flex-shrink-0" />
      High risk
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
        <p className="text-[11px] text-[#8A8480]/60 mt-1 font-normal normal-case tracking-normal leading-snug">
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
        <h1
          className="text-[1.875rem] font-bold text-foreground tracking-tight leading-tight mb-2.5"
          style={{ fontFamily: "var(--font-heading)" }}
        >
          New campaign
        </h1>
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
            className="w-full bg-secondary border border-border rounded-[11px] px-4 py-3 text-[14px] text-foreground placeholder:text-[#8A8480]/50 focus:outline-none focus:ring-2 focus:ring-[#315B4C]/20 focus:border-[#315B4C]/30 transition-all"
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
                ? "e.g. Zinc Oxide, Hyaluronic Acid, Niacinamide"
                : "e.g. Espresso No. 12, warm-neutral undertone"
            }
            className="w-full bg-secondary border border-border rounded-[11px] px-4 py-3 text-[14px] text-foreground placeholder:text-[#8A8480]/50 focus:outline-none focus:ring-2 focus:ring-[#315B4C]/20 focus:border-[#315B4C]/30 transition-all"
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
            className="w-full bg-card border border-border rounded-[18px] px-5 py-4 text-[14px] text-foreground placeholder:text-[#8A8480]/40 focus:outline-none focus:ring-2 focus:ring-[#315B4C]/15 focus:border-[#315B4C]/25 transition-all resize-none leading-[1.75] shadow-[inset_0_1px_3px_rgba(44,44,44,0.04)]"
          />
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
                      ? "bg-[#E2EDE9] border border-[#B8D0C6]"
                      : "bg-[#EEF5F2] border border-transparent hover:border-[#C7D7CE]/60"
                  )}
                >
                  <div
                    className={clsx(
                      "w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 transition-colors duration-150",
                      active ? "bg-[#315B4C]" : "bg-[#C7D7CE]"
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

          <div className="mt-5 px-5 py-4 rounded-[12px] bg-secondary border border-border">
            <p className="text-[12px] text-[#2C2C2C]/70 leading-[1.65]">
              <span className="font-semibold text-foreground">About this tool.</span>{" "}
              Aura reviews copy against FDA/MoCRA cosmetic-claim guidelines to help your team catch common claim issues before launch. This is compliance triage — not legal sign-off or regulatory approval. When in doubt, loop in your legal team.
            </p>
          </div>
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
          Sit tight — this usually takes about 10 seconds.
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
                    pending && "text-[#8A8480]/50 font-medium"
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

function ResultsScreen({ results, form, copiedId, onCopy, onReset }) {
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
      <div className="pt-6 mb-10 flex items-start justify-between gap-4">
        <div>
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
        <button
          onClick={onReset}
          className="mt-2 flex-shrink-0 text-[12px] font-medium text-muted-foreground hover:text-foreground border border-border px-3.5 py-2 rounded-[8px] transition-colors"
        >
          New campaign
        </button>
      </div>

      <div className="space-y-4">
        {results.map((result) => (
          <ResultCard key={result.channelId} result={result} copiedId={copiedId} onCopy={onCopy} />
        ))}
      </div>
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
            <RefreshCw size={14} strokeWidth={1.8} className="text-[#8A8480] flex-shrink-0" />
            <span className="text-[13px] font-semibold text-foreground">{result.channelLabel}</span>
          </div>
        </div>
        <div className="px-6 py-5">
          <p className="text-[14px] text-[#8A8480] leading-[1.75]">
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
            result.channelId === "email" ? (
              <EmailCard result={result} copiedId={copiedId} onCopy={onCopy} />
            ) : (
              <div className="px-6 py-5">
                <p className="text-[14px] text-foreground leading-[1.8] whitespace-pre-line">{result.copy}</p>
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

              <div className="bg-[#FAF0E4] border border-[#E8C9A8] rounded-[13px] px-4 py-4">
                <p className="text-[10px] font-bold text-[#9B5530] uppercase tracking-[0.1em] mb-1.5">
                  Here's the issue
                </p>
                <p className="text-[13px] text-[#7A4220] leading-[1.7]">{result.edit?.note}</p>
              </div>

              <div>
                <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-[0.1em] mb-2">
                  Suggested copy
                </p>
                <p className="text-[14px] text-foreground leading-[1.8] whitespace-pre-line">
                  {result.edit?.correctedCopy}
                </p>
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

// ─── Root ─────────────────────────────────────────────────────────────────────

export default function App() {
  const [step, setStep] = useState("input");
  const [form, setForm] = useState({
    brand: "tower_28",
    productName: "",
    productType: "skincare",
    adaptiveField: "",
    brief: "",
    channels: ["instagram", "tiktok"],
  });
  const [generatingStep, setGeneratingStep] = useState(0);
  const [copiedId, setCopiedId] = useState(null);

  const handleGenerate = useCallback(() => {
    setStep("generating");
    setGeneratingStep(0);
    GENERATING_STEPS.forEach((_, i) => {
      setTimeout(() => {
        setGeneratingStep(i + 1);
        if (i === GENERATING_STEPS.length - 1) {
          setTimeout(() => setStep("results"), 700);
        }
      }, (i + 1) * 1100);
    });
  }, []);

  const handleReset = useCallback(() => {
    setStep("input");
    setGeneratingStep(0);
  }, []);

  const handleCopy = useCallback((text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  }, []);

  const activeResults = ALL_RESULTS.filter((r) => form.channels.includes(r.channelId));

  return (
    <div className="min-h-screen bg-background">
      <TopNav step={step} onReset={handleReset} />
      <main className="pt-[52px]">
        {step === "input" && (
          <InputScreen form={form} setForm={setForm} onGenerate={handleGenerate} />
        )}
        {step === "generating" && <GeneratingScreen activeStep={generatingStep} />}
        {step === "results" && (
          <ResultsScreen
            results={activeResults}
            form={form}
            copiedId={copiedId}
            onCopy={handleCopy}
            onReset={handleReset}
          />
        )}
      </main>
    </div>
  );
}
