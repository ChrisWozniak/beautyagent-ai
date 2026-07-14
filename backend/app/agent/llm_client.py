"""LiteLLM client helpers for backend-only model calls."""

from __future__ import annotations

from typing import Any

from ..config import Settings
from ..models.request_models import Channel, GenerateRequest
from .prompts import build_draft_prompt


class LLMClientError(RuntimeError):
    """Raised when a backend LLM call is unavailable or fails."""


class LLMDraftError(RuntimeError):
    """Raised when LLM drafting is unavailable or fails."""


def _openrouter_model_name(model: str) -> str:
    if model.startswith("openrouter/"):
        return model

    return f"openrouter/{model}"


def _model_and_key(settings: Settings, anthropic_model: str) -> tuple[str, str]:
    if settings.anthropic_api_key:
        return anthropic_model, settings.anthropic_api_key

    if settings.openrouter_api_key:
        return _openrouter_model_name(settings.openrouter_model), settings.openrouter_api_key

    raise LLMClientError("ANTHROPIC_API_KEY or OPENROUTER_API_KEY is not configured.")


def _extract_text(response: Any) -> str:
    try:
        content = response.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as exc:
        raise LLMClientError("LiteLLM response did not include message content.") from exc

    if not isinstance(content, str) or not content.strip():
        raise LLMClientError("LiteLLM response content was empty.")

    return content.strip()


def complete_messages(
    messages: list[dict[str, str]],
    settings: Settings,
    anthropic_model: str,
    *,
    temperature: float,
    max_tokens: int | None = None,
) -> str:
    """Call the configured backend LLM and return plain text content."""
    try:
        from litellm import completion
    except ImportError as exc:
        raise LLMClientError("LiteLLM is not installed.") from exc

    model, api_key = _model_and_key(settings, anthropic_model)

    try:
        response = completion(
            model=model,
            messages=messages,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens or settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )
    except Exception as exc:
        raise LLMClientError("LiteLLM call failed.") from exc

    return _extract_text(response)


def generate_draft_with_llm(
    request: GenerateRequest,
    channel: Channel,
    brand_config: dict[str, Any],
    safe_claim: str,
    settings: Settings,
) -> str:
    try:
        return complete_messages(
            messages=build_draft_prompt(request, channel, brand_config, safe_claim),
            settings=settings,
            anthropic_model=settings.anthropic_model_sonnet,
            temperature=0.7,
            max_tokens=settings.llm_max_tokens,
        )
    except LLMClientError as exc:
        raise LLMDraftError("LiteLLM drafting failed.") from exc
