"""BeautyAgent orchestration for the backend MVP."""

from __future__ import annotations

import asyncio
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from ..config_loader import ConfigLoadError, load_json_config
from ..config import get_settings
from ..models.request_models import Channel, GenerateRequest
from ..models.response_models import ChannelError, ChannelResult, GenerateResponse
from ..tools.check_brand_voice import VOICE_CONFIDENCE_THRESHOLD, check_brand_voice
from ..tools.check_compliance import COMPLIANCE_CONFIDENCE_THRESHOLD, check_compliance
from .llm_client import LLMDraftError, generate_draft_with_llm


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BRAND_CONFIGS_PATH = DATA_DIR / "brand_configs.json"
PRODUCT_CONFIGS_PATH = DATA_DIR / "product_configs_richer_DRAFT.json"
BRAND_VOICE_PROFILE_PATHS = {
    "tower_28": DATA_DIR / "brand_voice_tower28.md",
    "half_magic": DATA_DIR / "brand_voice_halfmagic.md",
}
CHANNEL_ALIASES: dict[Channel, tuple[str, ...]] = {
    "tiktok": ("tiktok", "tik tok"),
    "instagram": ("instagram", "ig"),
    "email": ("email",),
}
GENERATION_NOTE_PATTERNS = (
    r"\n\s*-{3,}\s*(?:\n|$).*",
    r"\s+-{3,}\s*\*{0,2}note\s*:",
    r"\s+\*{0,2}note\s*:",
    r"\s+\*{0,2}compliance note\s*:",
    r"\s+\*{0,2}explanation\s*:",
    r"\s+\*{0,2}reasoning\s*:",
)
CHANNEL_START_PATTERNS: dict[Channel, tuple[re.Pattern[str], ...]] = {
    "tiktok": (
        re.compile(r"(?im)^\s*hook\s*:"),
        re.compile(r"(?im)^\s*script\s*:"),
        re.compile(r"(?im)^\s*cta\s*:"),
    ),
    "instagram": (
        re.compile(r"(?im)^\s*(?:caption|instagram caption)\s*:"),
        re.compile(r"(?im)^\s*(?:hook|cta)\s*:"),
    ),
    "email": (
        re.compile(r"(?im)^\s*subject\s*:"),
        re.compile(r"(?im)^\s*body\s*:"),
    ),
}


def _agent_trace_enabled() -> bool:
    return os.getenv("AGENT_TRACE", "").strip().lower() in {"1", "true", "yes", "on"}


def _trace_agent_step(channel: Channel, step: str, **fields: Any) -> None:
    if not _agent_trace_enabled():
        return

    details = " ".join(f"{key}={value}" for key, value in fields.items())
    suffix = f" {details}" if details else ""
    print(f"[agent-trace] channel={channel} step={step}{suffix}", flush=True)


def _strip_leading_reasoning(text: str, channel: Channel) -> str:
    matches = [
        match
        for pattern in CHANNEL_START_PATTERNS[channel]
        if (match := pattern.search(text)) is not None
    ]
    if not matches:
        return text

    first_start = min(match.start() for match in matches)
    leading_text = text[:first_start].strip()
    if not leading_text:
        return text

    if re.search(r"\b(?:no|cannot|can't|can not|we can|instead|but)\b", leading_text, re.IGNORECASE):
        return text[first_start:].lstrip()

    return text


def _strip_generation_notes(text: str, channel: Channel) -> str:
    """Remove LLM reasoning leaked after the generated draft copy."""
    cleaned = _strip_leading_reasoning(text.strip(), channel)
    for pattern in GENERATION_NOTE_PATTERNS:
        cleaned = re.split(
            pattern,
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE | re.DOTALL,
        )[0].strip()

    return cleaned


class DraftGenerator(Protocol):
    def __call__(self, request: GenerateRequest, channel: Channel) -> str:
        """Generate a raw draft for one requested channel."""


class BrandVoiceChecker(Protocol):
    def __call__(
        self,
        text: str,
        brand_id: str,
        brand_config: dict[str, Any],
        channel: str,
    ) -> dict[str, Any]:
        """Evaluate brand voice for one generated channel draft."""


@lru_cache(maxsize=1)
def load_brand_configs() -> dict[str, dict[str, Any]]:
    payload = load_json_config(BRAND_CONFIGS_PATH, "brand")
    brands = payload["brands"]
    for brand_id, profile_path in BRAND_VOICE_PROFILE_PATHS.items():
        brands[brand_id]["voice"] = profile_path.read_text(encoding="utf-8").rstrip("\n")

    return brands


@lru_cache(maxsize=1)
def load_product_configs() -> dict[str, list[dict[str, Any]]]:
    payload = load_json_config(PRODUCT_CONFIGS_PATH, "product")
    return {
        brand_id: products
        for brand_id, products in payload.items()
        if brand_id != "_meta"
    }


def _find_product_config(request: GenerateRequest) -> dict[str, Any] | None:
    normalized_name = request.productName.lower()
    for product in load_product_configs().get(request.brandId, []):
        if product["productName"].lower() == normalized_name:
            return product

    return None


def product_belongs_to_brand(brand_id: str, product_name: str) -> bool:
    normalized_name = product_name.lower().strip()
    return any(
        product["productName"].lower() == normalized_name
        for product in load_product_configs().get(brand_id, [])
    )


def _safe_claim_for_request(request: GenerateRequest) -> str:
    product_config = _find_product_config(request)
    if product_config and product_config.get("safe_claims"):
        return product_config["safe_claims"][0]

    if product_config and product_config.get("officialMarketingClaims"):
        return product_config["officialMarketingClaims"][0]

    if product_config and product_config.get("category"):
        return _safe_claim_for_category(product_config["category"])

    return "adds an easy, expressive finish to your beauty routine"


def _safe_claim_for_category(category: str) -> str:
    normalized = category.lower()
    if "spray" in normalized:
        return "refreshes skin throughout the day"
    if "concealer" in normalized:
        return "helps even the look of your complexion"
    if "mascara" in normalized:
        return "adds visible lift and definition to lashes"
    if "blush" in normalized:
        return "adds a soft wash of buildable color"
    if "glitter" in normalized:
        return "adds playful sparkle to any look"
    if "eyeliner" in normalized or "eye paint" in normalized or "liner" in normalized:
        return "creates expressive eye looks"
    if "lip" in normalized:
        return "adds a polished lip finish"
    if "gem" in normalized:
        return "creates playful, light-catching detail"
    if "tool" in normalized:
        return "helps guide a cleaner makeup application"

    return "adds an easy, expressive finish to your beauty routine"


def _fallback_copy_for_request(request: GenerateRequest) -> dict[str, str]:
    product_config = _find_product_config(request) or {}
    fallback_copy = product_config.get("fallback_copy", {})
    category_fallback = _fallback_copy_for_category(product_config.get("category", ""))
    return {
        "tiktok_hook": fallback_copy.get("tiktok_hook", category_fallback["tiktok_hook"]),
        "tiktok_cta": fallback_copy.get(
            "tiktok_cta",
            category_fallback["tiktok_cta"],
        ),
        "instagram_closer": fallback_copy.get(
            "instagram_closer",
            category_fallback["instagram_closer"],
        ),
        "email_finish": fallback_copy.get(
            "email_finish",
            category_fallback["email_finish"],
        ),
    }


def _fallback_copy_for_category(category: str) -> dict[str, str]:
    normalized = category.lower()
    if "spray" in normalized:
        return {
            "tiktok_hook": "is your quick skin refresh",
            "tiktok_cta": "Spritz it into your routine whenever your skin wants a fresh reset.",
            "instagram_closer": "Keep it close for the moments when your skin wants a calm, fresh reset.",
            "email_finish": "with a fresh, easy finish that fits naturally into your day.",
        }
    if "concealer" in normalized:
        return {
            "tiktok_hook": "is your quick complexion reset",
            "tiktok_cta": "Tap it on where your look wants a smoother, more even finish.",
            "instagram_closer": "Keep it close for the moments when your complexion wants a quick polish.",
            "email_finish": "with a natural-looking finish that keeps your routine easy.",
        }
    if "mascara" in normalized:
        return {
            "tiktok_hook": "is your quick lash reset",
            "tiktok_cta": "Sweep it on when your lashes want more visible lift and definition.",
            "instagram_closer": "Reach for it when your lash look wants a little more movement.",
            "email_finish": "with a lifted lash look that feels easy to wear.",
        }
    if "blush" in normalized:
        return {
            "tiktok_hook": "is your quick cheek reset",
            "tiktok_cta": "Blend it on when your look wants a soft pop of color.",
            "instagram_closer": "Keep it close for the moments when your cheeks want a fresh flush.",
            "email_finish": "with a soft color finish that warms up your look.",
        }
    if "lip" in normalized:
        return {
            "tiktok_hook": "is your quick lip reset",
            "tiktok_cta": "Swipe it on when your lip look wants a little more polish.",
            "instagram_closer": "Keep it close for the moments when your lip look wants a fresh finish.",
            "email_finish": "with a polished lip finish that fits naturally into your day.",
        }
    if "glitter" in normalized or "gem" in normalized:
        return {
            "tiktok_hook": "is your quick sparkle reset",
            "tiktok_cta": "Press it on when your look wants instant dimension.",
            "instagram_closer": "Keep it close for the moments when your look wants a little more light.",
            "email_finish": "with light-catching detail that makes the look feel finished.",
        }
    if "eyeliner" in normalized or "eye paint" in normalized or "liner" in normalized:
        return {
            "tiktok_hook": "is your quick eye-look reset",
            "tiktok_cta": "Paint it on when your look needs a bolder mood.",
            "instagram_closer": "Reach for it when your eye look wants more color, more play, and more edge.",
            "email_finish": "with a bold finish that keeps the look expressive.",
        }
    if "tool" in normalized:
        return {
            "tiktok_hook": "is your quick makeup guide",
            "tiktok_cta": "Use it when your look wants a cleaner, more confident shape.",
            "instagram_closer": "Keep it close for the moments when your routine wants an easier guide.",
            "email_finish": "with a simple guide that helps your makeup routine feel more controlled.",
        }

    return {
        "tiktok_hook": "is your quick beauty reset",
        "tiktok_cta": "Bring it into your routine whenever your look wants a fresh start.",
        "instagram_closer": "Keep it close for the moments when your beauty routine wants a fresh reset.",
        "email_finish": "with a polished finish that fits naturally into your day.",
    }


def draft_channel_copy(request: GenerateRequest, channel: Channel) -> str:
    brand = load_brand_configs()[request.brandId]
    brand_name = brand["display_name"]
    safe_claim = _safe_claim_for_request(request)
    fallback_copy = _fallback_copy_for_request(request)

    if channel == "tiktok":
        return (
            f"Hook: {request.productName} {fallback_copy['tiktok_hook']}.\n\n"
            f"Script: Meet {request.productName} from {brand_name}. It {safe_claim}, "
            f"while keeping the vibe true to {brand_name}.\n\n"
            f"CTA: {fallback_copy['tiktok_cta']}"
        )

    if channel == "instagram":
        return (
            f"Meet {request.productName} from {brand_name}: an easy routine staple that "
            f"{safe_claim}.\n\n"
            f"{fallback_copy['instagram_closer']}"
        )

    return (
        f"Subject: A fresh reset from {brand_name}\n\n"
        "Body: "
        f"{request.productName} brings an easy beauty update to your routine. "
        f"It {safe_claim}, {fallback_copy['email_finish']}"
    )


def draft_channel_with_optional_llm(request: GenerateRequest, channel: Channel) -> str:
    settings = get_settings()
    if not settings.use_llm_drafting:
        return draft_channel_copy(request, channel)

    brand = load_brand_configs()[request.brandId]
    safe_claim = _safe_claim_for_request(request)

    try:
        return generate_draft_with_llm(request, channel, brand, safe_claim, settings)
    except LLMDraftError:
        return draft_channel_copy(request, channel)


def _combine_unique(first: list[str], second: list[str]) -> list[str]:
    combined: list[str] = []
    for phrase in first + second:
        if phrase not in combined:
            combined.append(phrase)

    return combined


def _combine_explanations(first: str | None, second: str | None) -> str:
    parts: list[str] = []
    seen_keys: set[str] = set()
    for part in [first, second]:
        if not part:
            continue

        key = part.removeprefix("Marketer brief also included risky language: ")
        if key in seen_keys:
            continue

        parts.append(part)
        seen_keys.add(key)

    return " ".join(parts)


def _merge_audits(draft_audit: dict[str, Any], brief_audit: dict[str, Any]) -> dict[str, Any]:
    if brief_audit["compliance_status"] == "PASSED":
        return draft_audit

    flagged_phrases = _combine_unique(
        draft_audit["flagged_phrases"],
        brief_audit["flagged_phrases"],
    )
    explanation = _combine_explanations(
        draft_audit["explanation"],
        f"Marketer brief also included risky language: {brief_audit['explanation']}",
    )

    return {
        "compliance_status": "FAILED",
        "compliance_confidence": min(
            draft_audit.get("compliance_confidence", 1.0),
            brief_audit.get("compliance_confidence", 1.0),
        ),
        "flagged_phrases": flagged_phrases,
        "explanation": explanation,
        "detection_source": "deterministic",
        "final_safe_output": draft_audit["final_safe_output"],
    }


def _needs_voice_review(voice_result: dict[str, Any]) -> bool:
    return voice_result["voice_confidence"] < VOICE_CONFIDENCE_THRESHOLD


def _voice_review_result(
    channel: Channel,
    raw_draft: str,
    voice_result: dict[str, Any],
) -> ChannelResult:
    return ChannelResult(
        channel=channel,
        generation_status="completed",
        raw_draft=raw_draft,
        voice_status=voice_result["voice_status"],
        voice_confidence=voice_result["voice_confidence"],
        voice_reason=voice_result["voice_reason"],
        compliance_status="NEEDS_HUMAN_REVIEW",
        compliance_confidence=None,
        flagged_phrases=None,
        explanation=None,
        detection_source=None,
        final_safe_output=None,
        retry_exhausted=None,
        escalation_trigger="voice",
        error=None,
    )


def _voice_blocked_compliance_failure_result(
    channel: Channel,
    raw_draft: str,
    voice_result: dict[str, Any],
    compliance_result: dict[str, Any],
) -> ChannelResult:
    return ChannelResult(
        channel=channel,
        generation_status="completed",
        raw_draft=raw_draft,
        voice_status=voice_result["voice_status"],
        voice_confidence=voice_result["voice_confidence"],
        voice_reason=voice_result["voice_reason"],
        compliance_status=compliance_result["compliance_status"],
        compliance_confidence=compliance_result.get("compliance_confidence"),
        flagged_phrases=compliance_result.get("flagged_phrases"),
        explanation=compliance_result.get("explanation"),
        detection_source=compliance_result.get("detection_source"),
        final_safe_output=compliance_result.get("final_safe_output"),
        retry_exhausted=None,
        escalation_trigger="compliance",
        error=None,
    )


def _needs_compliance_review(compliance_result: dict[str, Any]) -> bool:
    confidence = compliance_result.get("compliance_confidence")
    if compliance_result["compliance_status"] == "NEEDS_HUMAN_REVIEW":
        return True

    return isinstance(confidence, (int, float)) and confidence < COMPLIANCE_CONFIDENCE_THRESHOLD


def _compliance_review_result(
    channel: Channel,
    raw_draft: str,
    voice_result: dict[str, Any],
    compliance_result: dict[str, Any],
) -> ChannelResult:
    return ChannelResult(
        channel=channel,
        generation_status="completed",
        raw_draft=raw_draft,
        voice_status=voice_result["voice_status"],
        voice_confidence=voice_result["voice_confidence"],
        voice_reason=voice_result["voice_reason"],
        compliance_status="NEEDS_HUMAN_REVIEW",
        compliance_confidence=compliance_result.get("compliance_confidence"),
        flagged_phrases=compliance_result.get("flagged_phrases"),
        explanation=compliance_result.get("explanation"),
        detection_source=compliance_result.get("detection_source"),
        final_safe_output=None,
        retry_exhausted=None,
        escalation_trigger="compliance",
        error=None,
    )


def _channel_mentions(text: str) -> set[Channel]:
    lowered = text.lower()
    mentions: set[Channel] = set()

    for channel, aliases in CHANNEL_ALIASES.items():
        for alias in aliases:
            if re.search(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", lowered):
                mentions.add(channel)
                break

    return mentions


def _brief_for_channel_audit(brief: str, channel: Channel) -> str:
    if not _channel_mentions(brief):
        return brief

    segments = re.split(r"(?<=[.!?])\s+|;\s+|,\s+but\s+|\s+but\s+", brief)
    scoped_segments: list[str] = []

    for segment in segments:
        cleaned = segment.strip()
        if not cleaned:
            continue

        mentions = _channel_mentions(cleaned)
        if not mentions or channel in mentions:
            scoped_segments.append(cleaned)

    return " ".join(scoped_segments) if scoped_segments else brief


def process_channel_loop(
    request: GenerateRequest,
    channel: Channel,
    draft_generator: DraftGenerator = draft_channel_with_optional_llm,
    brand_voice_checker: BrandVoiceChecker | None = None,
) -> ChannelResult:
    """Run draft, brand voice gate, deterministic audit, and final backstop."""
    brand = load_brand_configs()[request.brandId]
    resolved_voice_checker = brand_voice_checker or check_brand_voice
    _trace_agent_step(channel, "start", brand_id=request.brandId)
    raw_draft = draft_generator(request, channel)
    raw_draft = _strip_generation_notes(raw_draft, channel)
    _trace_agent_step(channel, "draft_generated", draft_chars=len(raw_draft))
    draft_audit = check_compliance(raw_draft)
    brief_audit = check_compliance(_brief_for_channel_audit(request.brief, channel))
    first_audit = _merge_audits(draft_audit, brief_audit)
    _trace_agent_step(
        channel,
        "deterministic_precheck",
        compliance_status=first_audit["compliance_status"],
        compliance_confidence=first_audit.get("compliance_confidence"),
    )
    voice_result = resolved_voice_checker(raw_draft, request.brandId, brand, channel)
    _trace_agent_step(
        channel,
        "brand_voice_checked",
        voice_status=voice_result["voice_status"],
        voice_confidence=voice_result["voice_confidence"],
    )

    if _needs_voice_review(voice_result):
        if first_audit["compliance_status"] == "FAILED":
            _trace_agent_step(channel, "routed_to_human_review", trigger="compliance")
            return _voice_blocked_compliance_failure_result(
                channel,
                raw_draft,
                voice_result,
                first_audit,
            )

        _trace_agent_step(channel, "routed_to_human_review", trigger="voice")
        return _voice_review_result(channel, raw_draft, voice_result)

    if _needs_compliance_review(first_audit):
        _trace_agent_step(channel, "routed_to_human_review", trigger="compliance")
        return _compliance_review_result(channel, raw_draft, voice_result, first_audit)

    final_safe_output = first_audit["final_safe_output"]
    final_backstop = check_compliance(final_safe_output)
    _trace_agent_step(
        channel,
        "final_backstop_checked",
        compliance_status=final_backstop["compliance_status"],
    )

    flagged_phrases = first_audit["flagged_phrases"]
    explanation = first_audit["explanation"]
    detection_source = first_audit["detection_source"]
    retry_exhausted = None

    if final_backstop["compliance_status"] == "FAILED":
        flagged_phrases = _combine_unique(
            flagged_phrases,
            final_backstop["flagged_phrases"],
        )
        explanation = _combine_explanations(
            explanation,
            "Final deterministic backstop still found risky language.",
        )
        detection_source = "deterministic"
        final_safe_output = final_backstop["final_safe_output"]
        if check_compliance(final_safe_output)["compliance_status"] == "FAILED":
            retry_exhausted = True

    result_confidence = first_audit.get("compliance_confidence", 1.0)
    _trace_agent_step(
        channel,
        "completed",
        compliance_status=first_audit["compliance_status"],
        retry_exhausted=retry_exhausted,
    )
    return ChannelResult(
        channel=channel,
        generation_status="completed",
        raw_draft=raw_draft,
        voice_status=voice_result["voice_status"],
        voice_confidence=voice_result["voice_confidence"],
        voice_reason=voice_result["voice_reason"],
        compliance_status=first_audit["compliance_status"],
        compliance_confidence=result_confidence,
        flagged_phrases=flagged_phrases,
        explanation=explanation,
        detection_source=detection_source,
        final_safe_output=final_safe_output,
        retry_exhausted=retry_exhausted,
        escalation_trigger=None,
        error=None,
    )


def channel_error_result(channel: Channel, code: str, message: str) -> ChannelResult:
    return ChannelResult(
        channel=channel,
        generation_status="error",
        raw_draft=None,
        voice_status=None,
        voice_confidence=None,
        voice_reason=None,
        compliance_status=None,
        compliance_confidence=None,
        flagged_phrases=None,
        explanation=None,
        detection_source=None,
        final_safe_output=None,
        retry_exhausted=None,
        escalation_trigger=None,
        error=ChannelError(code=code, message=message),
    )


def _classify_channel_exception(exc: Exception) -> tuple[str, str]:
    if isinstance(exc, TimeoutError):
        return "TIMEOUT", "Generation timed out after retries."

    if isinstance(exc, LLMDraftError) and "rate" in str(exc).lower():
        return "RATE_LIMITED", "That channel's LLM call was rate limited."

    return "TOOL_ERROR", "Channel generation failed before completion."


async def process_channel_safely(request: GenerateRequest, channel: Channel) -> ChannelResult:
    try:
        settings = get_settings()
        return await asyncio.wait_for(
            asyncio.to_thread(process_channel_loop, request, channel),
            timeout=settings.channel_timeout_seconds,
        )
    except asyncio.TimeoutError:
        return channel_error_result(channel, "TIMEOUT", "Generation timed out after retries.")
    except ConfigLoadError:
        raise
    except Exception as exc:
        code, message = _classify_channel_exception(exc)
        return channel_error_result(channel, code, message)


async def generate_mock_response(request: GenerateRequest) -> GenerateResponse:
    results = await asyncio.gather(
        *[
            process_channel_safely(request, channel)
            for channel in request.channels
        ],
    )

    return GenerateResponse(
        results=list(results),
        error=None,
    )
