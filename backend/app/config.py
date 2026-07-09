"""Runtime configuration for the BeautyAgent backend."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def _env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_str(name: str, default: str | None = None) -> str | None:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    value = raw_value.strip().strip('"').strip("'")
    return value or default


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = float(raw_value.strip())
    except ValueError:
        return default

    if value <= 0:
        return default

    return value


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value.strip())
    except ValueError:
        return default

    if value <= 0:
        return default

    return value


@dataclass(frozen=True)
class Settings:
    openrouter_api_key: str | None
    openrouter_model: str
    use_llm_drafting: bool
    llm_timeout_seconds: float
    llm_max_tokens: int
    channel_timeout_seconds: float


def get_settings() -> Settings:
    return Settings(
        openrouter_api_key=_env_str("OPENROUTER_API_KEY"),
        openrouter_model=_env_str("OPENROUTER_MODEL", "poolside/laguna-m.1:free")
        or "poolside/laguna-m.1:free",
        use_llm_drafting=_env_flag("USE_LLM_DRAFTING", default=False),
        llm_timeout_seconds=_env_float("LLM_TIMEOUT_SECONDS", default=15.0),
        llm_max_tokens=_env_int("LLM_MAX_TOKENS", default=1000),
        channel_timeout_seconds=_env_float("CHANNEL_TIMEOUT_SECONDS", default=20.0),
    )

