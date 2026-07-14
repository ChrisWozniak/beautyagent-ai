"""Prompt templates for BeautyAgent generation."""

from __future__ import annotations

from typing import Any

from ..models.request_models import Channel, GenerateRequest


CHANNEL_INSTRUCTIONS: dict[Channel, str] = {
    "tiktok": (
        "Write a short TikTok script with a hook, 2-3 spoken lines, and a soft CTA. "
        "Make it easy to scan in a results card."
    ),
    "instagram": (
        "Write a polished Instagram caption with one clear beauty benefit, 1-2 short "
        "paragraphs, and optional light hashtags."
    ),
    "email": (
        "Write a short email draft. Start with 'Subject:' on its own line, then 'Body:' "
        "with concise body copy."
    ),
}

CHANNEL_FORMATS: dict[Channel, str] = {
    "tiktok": "Format exactly as: Hook: ... then Script: ... then CTA: ...",
    "instagram": "Format as caption copy only. No labels unless they are natural to the caption.",
    "email": "Format exactly as: Subject: ... then a blank line then Body: ...",
}


def build_draft_prompt(
    request: GenerateRequest,
    channel: Channel,
    brand_config: dict[str, Any],
    safe_claim: str,
) -> list[dict[str, str]]:
    compliance_notes = brand_config.get("compliance_notes") or []
    compliance_notes_text = "\n".join(
        f"- {note}" for note in compliance_notes
    ) or "- Keep claims cosmetic, appearance-focused, and compliant."

    system_prompt = (
        "You are BeautyAgent AI, drafting cosmetic marketing copy for a beauty brand. "
        "Keep claims cosmetic, appearance-focused, and compliant. Avoid disease, cure, "
        "heal, anti-inflammatory, guaranteed-result, or skin-structure claims. "
        "Return only the draft copy, with no explanation or compliance analysis."
    )

    user_prompt = "\n".join(
        [
            f"Brand: {brand_config['display_name']}",
            f"Brand voice: {brand_config['voice']}",
            f"Brand compliance notes:\n{compliance_notes_text}",
            f"Product: {request.productName}",
            f"Core actives: {request.coreActives or 'not provided'}",
            f"Channel: {channel}",
            f"Channel instruction: {CHANNEL_INSTRUCTIONS[channel]}",
            f"Required output format: {CHANNEL_FORMATS[channel]}",
            f"Safe claim to lean on: {safe_claim}",
            f"Marketer brief: {request.brief}",
        ]
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

