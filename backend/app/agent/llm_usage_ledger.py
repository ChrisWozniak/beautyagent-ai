"""Local-only persistent ledger for backend LLM usage metadata."""

from __future__ import annotations

import json
import os
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from .llm_client import LLMUsageRecord


BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_LEDGER_PATH = BACKEND_DIR / "logs" / "llm_usage_local.jsonl"


def llm_usage_ledger_path() -> Path:
    configured_path = os.getenv("LLM_USAGE_LEDGER_PATH")
    if configured_path:
        return Path(configured_path)

    return DEFAULT_LEDGER_PATH


def append_llm_usage_record(record: "LLMUsageRecord") -> None:
    path = llm_usage_ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        **asdict(record),
    }

    with path.open("a", encoding="utf-8") as ledger_file:
        ledger_file.write(json.dumps(payload, sort_keys=True) + "\n")


def _numeric_value(payload: dict[str, Any], key: str) -> int | float | None:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None

    return value


def summarize_llm_usage_ledger(path: Path | None = None) -> dict[str, int | float | None]:
    ledger_path = path or llm_usage_ledger_path()
    if not ledger_path.exists():
        return {
            "calls": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "total_tokens": None,
            "cost_usd": None,
        }

    calls = 0
    prompt_tokens = 0
    completion_tokens = 0
    total_tokens = 0
    cost_usd = 0.0
    has_prompt = False
    has_completion = False
    has_total = False
    has_cost = False

    for line in ledger_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(payload, dict):
            continue

        calls += 1
        prompt = _numeric_value(payload, "prompt_tokens")
        completion = _numeric_value(payload, "completion_tokens")
        total = _numeric_value(payload, "total_tokens")
        cost = _numeric_value(payload, "cost_usd")

        if prompt is not None:
            prompt_tokens += int(prompt)
            has_prompt = True
        if completion is not None:
            completion_tokens += int(completion)
            has_completion = True
        if total is not None:
            total_tokens += int(total)
            has_total = True
        if cost is not None:
            cost_usd += float(cost)
            has_cost = True

    return {
        "calls": calls,
        "prompt_tokens": prompt_tokens if has_prompt else None,
        "completion_tokens": completion_tokens if has_completion else None,
        "total_tokens": total_tokens if has_total else None,
        "cost_usd": round(cost_usd, 8) if has_cost else None,
    }
