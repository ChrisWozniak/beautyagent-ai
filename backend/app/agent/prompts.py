"""Prompt templates for BeautyAgent generation."""

from __future__ import annotations

from typing import Any

from ..models.request_models import Channel, GenerateRequest


CHANNEL_INSTRUCTIONS: dict[Channel, str] = {
    "tiktok": (
        "Write a short TikTok script with a hook, demo/script, and a soft low-pressure CTA. "
        "Friend/creator voice - casual, conversational, real. "
        "Tower 28: approachable and skin-first, <150 chars per section. "
        "Half Magic: fast, tutorial/trend style, backstage-friend energy, <100-char caption. "
        "No hashtags in the script body."
    ),
    "instagram": (
        "Write an Instagram caption. Hook first, then 1-2 short paragraphs, then CTA. "
        "Tower 28: 75-250 words, 1-3 emoji max, CTA 'find your shade' or 'shop now', zero hashtags. "
        "Half Magic: 100-250 words, hook-first, moderate emoji, CTA 'tag us' or 'shop now', zero hashtags. "
        "No hashtag blocks. No more than 3 emoji total."
    ),
    "email": (
        "Write a short email. Start with 'Subject:' on its own line, then 'Body:' with concise copy. "
        "Tower 28: benefit-driven subject line, 30-50 chars, 0-1 emoji, warm and reassuring tone. "
        "Half Magic: playful/curious subject line, 25-45 chars, casual and expressive tone. "
        "Body should be 3-5 sentences max. One clear CTA. No bullet points."
    ),
}

CHANNEL_FORMATS: dict[Channel, str] = {
    "tiktok": (
        "Format exactly as:\n"
        "Hook: [one punchy line]\n"
        "Script: [2-3 casual spoken lines]\n"
        "CTA: [one soft, low-pressure line]"
    ),
    "instagram": (
        "Format as caption copy only. "
        "No section labels. Natural paragraph breaks. "
        "End with a single CTA line. No hashtag block."
    ),
    "email": (
        "Format exactly as:\n"
        "Subject: [subject line, 30-50 chars]\n"
        "\n"
        "Body:\n"
        "[3-5 sentence body]\n"
        "\n"
        "[Single CTA line]"
    ),
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
        "Return only the requested channel's draft copy. Do not include reasoning, "
        "compliance analysis, notes, refusals, markdown dividers, or draft labels for "
        "other channels."
    )

    prompt_lines = [
        f"Brand: {brand_config['display_name']}",
        f"Brand voice: {brand_config['voice']}",
        f"Brand compliance notes:\n{compliance_notes_text}",
        f"Product: {request.productName}",
        f"Use the product name exactly as written: {request.productName}",
    ]
    if request.coreActives:
        prompt_lines.append(f"Product detail: {request.coreActives}")

    prompt_lines.extend(
        [
            f"Channel: {channel}",
            f"Channel instruction: {CHANNEL_INSTRUCTIONS[channel]}",
            f"Required output format: {CHANNEL_FORMATS[channel]}",
            f"Safe claim to lean on: {safe_claim}",
            f"Marketer brief: {request.brief}",
            "Output constraints:",
            "- Write copy for this channel only, even if the brief mentions other channels.",
            "- Do not include labels for other channels such as EMAIL SUBJECT LINE or INSTAGRAM CAPTION.",
            "- Do not include compliance reasoning, refusals, explanations, notes, or markdown dividers.",
            "- Preserve the product name spelling exactly wherever it appears.",
        ]
    )

    user_prompt = "\n".join(prompt_lines)

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

