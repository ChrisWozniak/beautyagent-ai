"""BeautyAgent orchestration for the backend MVP."""

from __future__ import annotations

import asyncio
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

from ..config import get_settings
from ..models.request_models import Channel, GenerateRequest
from ..models.response_models import ChannelError, ChannelResult, GenerateResponse
from ..tools.check_compliance import check_compliance
from .llm_client import LLMDraftError, generate_draft_with_llm


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BRAND_CONFIGS_PATH = DATA_DIR / "brand_configs.json"
PRODUCT_CONFIGS_PATH = DATA_DIR / "product_configs.json"

CHANNEL_LABELS: dict[Channel, str] = {
    "tiktok": "TikTok",
    "instagram": "Instagram",
    "email": "email",
}

CHANNEL_ARTICLES: dict[Channel, str] = {
    "tiktok": "a",
    "instagram": "an",
    "email": "an",
}


class DraftGenerator(Protocol):
    def __call__(self, request: GenerateRequest, channel: Channel) -> str:
        """Generate a raw draft for one requested channel."""


@lru_cache(maxsize=1)
def load_brand_configs() -> dict[str, dict[str, Any]]:
    with BRAND_CONFIGS_PATH.open(encoding="utf-8") as config_file:
        payload = json.load(config_file)

    return payload["brands"]


@lru_cache(maxsize=1)
def load_product_configs() -> list[dict[str, Any]]:
    with PRODUCT_CONFIGS_PATH.open(encoding="utf-8") as config_file:
        payload = json.load(config_file)

    return payload["products"]


def _find_product_config(request: GenerateRequest) -> dict[str, Any] | None:
    normalized_name = request.productName.lower()
    for product in load_product_configs():
        if product["brandId"] == request.brandId and product["name"].lower() == normalized_name:
            return product

    return None


def _safe_claim_for_request(request: GenerateRequest) -> str:
    product_config = _find_product_config(request)
    if product_config and product_config["safe_claims"]:
        return product_config["safe_claims"][0]

    return "keeps the message beauty-focused and compliant"


def draft_channel_copy(request: GenerateRequest, channel: Channel) -> str:
    brand = load_brand_configs()[request.brandId]
    brand_name = brand["display_name"]
    channel_label = CHANNEL_LABELS[channel]
    safe_claim = _safe_claim_for_request(request)

    if channel == "tiktok":
        return (
            f"{brand_name} {request.productName} is ready for your {channel_label} routine: "
            f"{safe_claim}, with a voice that is {brand['voice']}. "
            f"Brief direction: {request.brief}"
        )

    if channel == "instagram":
        return (
            f"Meet {request.productName} from {brand_name}. "
            f"Built for {CHANNEL_ARTICLES[channel]} {channel_label} moment, "
            f"it {safe_claim}. Brief direction: {request.brief}"
        )

    return (
        f"Subject: A fresh look from {brand_name}\n\n"
        f"{request.productName} brings an easy beauty update to your routine. "
        f"It {safe_claim}, while keeping the message clear and compliant. "
        f"Brief direction: {request.brief}"
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
    parts = [part for part in [first, second] if part]
    return " ".join(parts)


def process_channel_loop(
    request: GenerateRequest,
    channel: Channel,
    draft_generator: DraftGenerator = draft_channel_with_optional_llm,
) -> ChannelResult:
    """Run draft, deterministic audit, revision, and final backstop for a channel."""
    raw_draft = draft_generator(request, channel)
    first_audit = check_compliance(raw_draft)
    final_safe_output = first_audit["final_safe_output"]
    final_backstop = check_compliance(final_safe_output)

    flagged_phrases = first_audit["flagged_phrases"]
    explanation = first_audit["explanation"]
    detection_source = first_audit["detection_source"]
    retry_exhausted = False

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
        retry_exhausted = check_compliance(final_safe_output)["compliance_status"] == "FAILED"

    return ChannelResult(
        channel=channel,
        generation_status="completed",
        raw_draft=raw_draft,
        compliance_status=first_audit["compliance_status"],
        flagged_phrases=flagged_phrases,
        explanation=explanation,
        detection_source=detection_source,
        final_safe_output=final_safe_output,
        retry_exhausted=retry_exhausted,
        error=None,
    )


def channel_error_result(channel: Channel, code: str, message: str) -> ChannelResult:
    return ChannelResult(
        channel=channel,
        generation_status="error",
        raw_draft=None,
        compliance_status=None,
        flagged_phrases=None,
        explanation=None,
        detection_source=None,
        final_safe_output=None,
        retry_exhausted=None,
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
