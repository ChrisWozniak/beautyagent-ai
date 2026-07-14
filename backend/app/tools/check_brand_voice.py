"""LLM-backed brand voice evaluation for Week 2."""

from __future__ import annotations

import json
import re
from typing import Any

try:
    from strands import tool
except ImportError:
    def tool(func=None, **_kwargs):
        if func is None:
            return lambda wrapped: wrapped

        return func

from ..agent.llm_client import LLMClientError, complete_messages
from ..config import Settings, get_settings


VOICE_CONFIDENCE_THRESHOLD = 0.75


def _brand_voice_messages(
    text: str,
    brand_id: str,
    brand_config: dict[str, Any],
    channel: str,
) -> list[dict[str, str]]:
    display_name = brand_config.get("display_name", brand_id)
    voice_profile = brand_config.get("voice", "")

    return [
        {
            "role": "system",
            "content": (
                "You are BeautyAgent AI's Brand Voice Agent. Evaluate whether beauty "
                "marketing copy matches the supplied brand voice profile. Return only "
                "valid JSON with keys voice_status, voice_confidence, and voice_reason. "
                "Do not return plain text, Markdown, code fences, or explanations outside JSON."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Brand ID: {brand_id}\n"
                f"Brand name: {display_name}\n"
                f"Channel: {channel}\n"
                f"Brand voice profile:\n{voice_profile}\n\n"
                f"Draft copy:\n{text}\n\n"
                "Rules:\n"
                "- voice_status must be ON_VOICE or DRIFTED.\n"
                "- voice_confidence must be a number from 0.0 to 1.0.\n"
                "- voice_reason must be one short sentence citing a specific phrase, "
                "cadence, structural trait, emoji/caps usage, or channel fit.\n"
                "- Do not evaluate regulatory compliance here.\n"
                '- Example response: {"voice_status":"DRIFTED","voice_confidence":0.86,'
                '"voice_reason":"The sterile phrase protocol-grade skin maintenance '
                'misses the brand\'s friendly, conversational voice."}\n'
            ),
        },
    ]


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw_text, flags=re.DOTALL)
        if match is None:
            raise

        payload = json.loads(match.group(0))

    if not isinstance(payload, dict):
        raise ValueError("Brand voice response was not a JSON object.")

    return payload


def _normalize_brand_voice_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_status = str(payload.get("voice_status", "")).strip().upper()
    if raw_status not in {"ON_VOICE", "DRIFTED"}:
        raise ValueError("Brand voice response had invalid voice_status.")

    raw_confidence = payload.get("voice_confidence")
    if isinstance(raw_confidence, bool) or not isinstance(raw_confidence, (int, float)):
        raise ValueError("Brand voice response had invalid voice_confidence.")

    confidence = max(0.0, min(1.0, float(raw_confidence)))
    raw_reason = payload.get("voice_reason")
    if not isinstance(raw_reason, str) or not raw_reason.strip():
        raise ValueError("Brand voice response had empty voice_reason.")

    return {
        "voice_status": raw_status,
        "voice_confidence": confidence,
        "voice_reason": raw_reason.strip(),
    }


def _recover_plain_text_verdict(raw_text: str) -> dict[str, Any]:
    normalized = raw_text.strip()
    upper_text = normalized.upper()

    if not normalized:
        raise ValueError("Brand voice response was empty.")

    if "DRIFTED" in upper_text and "ON_VOICE" not in upper_text:
        return {
            "voice_status": "DRIFTED",
            "voice_confidence": 0.0,
            "voice_reason": (
                normalized
                if len(normalized) > len("DRIFTED")
                else "The model returned a DRIFTED verdict without structured JSON."
            ),
        }

    if "ON_VOICE" in upper_text and "DRIFTED" not in upper_text:
        return {
            "voice_status": "ON_VOICE",
            "voice_confidence": 1.0,
            "voice_reason": (
                normalized
                if len(normalized) > len("ON_VOICE")
                else "The model returned an ON_VOICE verdict without structured JSON."
            ),
        }

    raise ValueError("Brand voice response did not include a recoverable verdict.")


def _failed_brand_voice_result(reason: str) -> dict[str, Any]:
    return {
        "voice_status": "DRIFTED",
        "voice_confidence": 0.0,
        "voice_reason": reason,
    }


def check_brand_voice(
    text: str,
    brand_id: str,
    brand_config: dict[str, Any],
    channel: str,
    settings: Settings | None = None,
) -> dict[str, Any]:
    """Evaluate brand voice with Sonnet and fail closed to human review."""
    resolved_settings = settings or get_settings()

    try:
        raw_response = complete_messages(
            _brand_voice_messages(text, brand_id, brand_config, channel),
            resolved_settings,
            resolved_settings.anthropic_model_sonnet,
            temperature=0.0,
            max_tokens=350,
            call_name="brand_voice",
        )
        payload = _extract_json_object(raw_response)
        return _normalize_brand_voice_payload(payload)
    except (json.JSONDecodeError, ValueError):
        try:
            return _recover_plain_text_verdict(raw_response)
        except ValueError:
            return _failed_brand_voice_result(
                "Brand voice evaluation failed; needs human review before compliance audit."
            )
    except LLMClientError:
        return _failed_brand_voice_result(
            "Brand voice evaluation failed; needs human review before compliance audit."
        )


@tool
def check_brand_voice_tool(
    text: str,
    brand_id: str,
    brand_config: dict[str, Any],
    channel: str,
) -> dict[str, Any]:
    """Strands-compatible wrapper around brand voice evaluation."""
    return check_brand_voice(text, brand_id, brand_config, channel)
