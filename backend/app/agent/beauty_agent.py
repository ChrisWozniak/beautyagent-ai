"""Mock BeautyAgent orchestration for the backend MVP."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..models.request_models import Channel, GenerateRequest
from ..models.response_models import ChannelResult, GenerateResponse
from ..tools.check_compliance import check_compliance


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


def generate_channel_result(request: GenerateRequest, channel: Channel) -> ChannelResult:
    raw_draft = draft_channel_copy(request, channel)
    compliance = check_compliance(raw_draft)

    return ChannelResult(
        channel=channel,
        generation_status="completed",
        raw_draft=raw_draft,
        compliance_status=compliance["compliance_status"],
        flagged_phrases=compliance["flagged_phrases"],
        explanation=compliance["explanation"],
        detection_source=compliance["detection_source"],
        final_safe_output=compliance["final_safe_output"],
        retry_exhausted=False,
        error=None,
    )


def generate_mock_response(request: GenerateRequest) -> GenerateResponse:
    return GenerateResponse(
        results=[
            generate_channel_result(request, channel)
            for channel in request.channels
        ],
        error=None,
    )
