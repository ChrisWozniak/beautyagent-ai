"""LiteLLM client helpers for backend-only model calls."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock
from typing import Any

from ..config import Settings
from ..models.request_models import Channel, GenerateRequest
from .prompts import build_draft_prompt


class LLMClientError(RuntimeError):
    """Raised when a backend LLM call is unavailable or fails."""


class LLMDraftError(RuntimeError):
    """Raised when LLM drafting is unavailable or fails."""


@dataclass(frozen=True)
class LLMUsageRecord:
    call_name: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    cost_usd: float | None


_usage_records: list[LLMUsageRecord] = []
_usage_lock = Lock()


def reset_llm_usage() -> None:
    with _usage_lock:
        _usage_records.clear()


def get_llm_usage() -> list[LLMUsageRecord]:
    with _usage_lock:
        return list(_usage_records)


def summarize_llm_usage() -> dict[str, int | float | None]:
    records = get_llm_usage()
    known_prompt = [record.prompt_tokens for record in records if record.prompt_tokens is not None]
    known_completion = [
        record.completion_tokens
        for record in records
        if record.completion_tokens is not None
    ]
    known_total = [record.total_tokens for record in records if record.total_tokens is not None]
    known_costs = [record.cost_usd for record in records if record.cost_usd is not None]

    return {
        "calls": len(records),
        "prompt_tokens": sum(known_prompt) if known_prompt else None,
        "completion_tokens": sum(known_completion) if known_completion else None,
        "total_tokens": sum(known_total) if known_total else None,
        "cost_usd": round(sum(known_costs), 8) if known_costs else None,
    }


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


def _response_value(container: Any, key: str) -> Any:
    if isinstance(container, dict):
        return container.get(key)

    return getattr(container, key, None)


def _int_usage_value(usage: Any, *keys: str) -> int | None:
    for key in keys:
        value = _response_value(usage, key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)

    return None


def _response_cost(response: Any) -> float | None:
    hidden_params = _response_value(response, "_hidden_params")
    if not hidden_params:
        return None

    cost = _response_value(hidden_params, "response_cost")
    if isinstance(cost, bool) or not isinstance(cost, int | float):
        return None

    return float(cost)


def _record_usage(response: Any, model: str, call_name: str) -> None:
    usage = _response_value(response, "usage")
    if usage is None:
        return

    record = LLMUsageRecord(
        call_name=call_name,
        model=model,
        prompt_tokens=_int_usage_value(usage, "prompt_tokens", "input_tokens"),
        completion_tokens=_int_usage_value(
            usage,
            "completion_tokens",
            "output_tokens",
        ),
        total_tokens=_int_usage_value(usage, "total_tokens"),
        cost_usd=_response_cost(response),
    )
    with _usage_lock:
        _usage_records.append(record)


def complete_messages(
    messages: list[dict[str, str]],
    settings: Settings,
    anthropic_model: str,
    *,
    temperature: float,
    max_tokens: int | None = None,
    call_name: str = "llm",
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

    _record_usage(response, model, call_name)
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
            call_name="generation",
        )
    except LLMClientError as exc:
        raise LLMDraftError("LiteLLM drafting failed.") from exc
