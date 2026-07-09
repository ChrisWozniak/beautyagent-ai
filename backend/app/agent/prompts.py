"""Prompt templates for BeautyAgent generation."""

from __future__ import annotations

from typing import Any

from ..models.request_models import Channel, GenerateRequest


CHANNEL_INSTRUCTIONS: dict[Channel, str] = {
    "tiktok": "Write short social video copy with a lively hook and one concise benefit.",
    "instagram": "Write polished Instagram caption copy with one clear beauty benefit.",
    "email": "Write a short email-style draft with a subject line and concise body copy.",
}


def build_draft_prompt(
    request: GenerateRequest,
    channel: Channel,
    brand_config: dict[str, Any],
    safe_claim: str,
) -> list[dict[str, str]]:
    system_prompt = (
        "You are BeautyAgent AI, drafting cosmetic marketing copy for a beauty brand. "
        "Keep claims cosmetic, appearance-focused, and compliant. Avoid disease, cure, "
        "heal, anti-inflammatory, guaranteed-result, or skin-structure claims. "
        "Return only the draft copy, with no explanation."
    )

    user_prompt = "\n".join(
        [
            f"Brand: {brand_config['display_name']}",
            f"Brand voice: {brand_config['voice']}",
            f"Product: {request.productName}",
            f"Core actives: {request.coreActives or 'not provided'}",
            f"Channel: {channel}",
            f"Channel instruction: {CHANNEL_INSTRUCTIONS[channel]}",
            f"Safe claim to lean on: {safe_claim}",
            f"Marketer brief: {request.brief}",
        ]
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

