"""LiteLLM/OpenRouter drafting client."""

from __future__ import annotations

from typing import Any

from ..config import Settings
from ..models.request_models import Channel, GenerateRequest
from .prompts import build_draft_prompt


class LLMDraftError(RuntimeError):
    """Raised when LLM drafting is unavailable or fails."""


def _openrouter_model_name(model: str) -> str:
    if model.startswith("openrouter/"):
        return model

    return f"openrouter/{model}"


def _extract_text(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise LLMDraftError("LiteLLM response did not include message content.") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMDraftError("LiteLLM response content was empty.")

    return content.strip()


def generate_draft_with_llm(
    request: GenerateRequest,
    channel: Channel,
    brand_config: dict[str, Any],
    safe_claim: str,
    settings: Settings,
) -> str:
    if not settings.openrouter_api_key:
        raise LLMDraftError("OPENROUTER_API_KEY is not configured.")

    try:
        from litellm import completion
    except ImportError as exc:
        raise LLMDraftError("LiteLLM is not installed.") from exc

    try:
        response = completion(
            model=_openrouter_model_name(settings.openrouter_model),
            messages=build_draft_prompt(request, channel, brand_config, safe_claim),
            api_key=settings.openrouter_api_key,
            temperature=0.7,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )
    except Exception as exc:
        raise LLMDraftError("LiteLLM/OpenRouter drafting failed.") from exc

    return _extract_text(response)
