"""Console helpers for reporting backend LLM token usage."""

from __future__ import annotations

from backend.app.agent.llm_client import get_llm_usage, summarize_llm_usage
from backend.app.agent.llm_usage_ledger import (
    llm_usage_ledger_path,
    summarize_llm_usage_ledger,
)


def print_llm_usage_report() -> None:
    records = get_llm_usage()
    if not records:
        print("\nLLM usage: no usage metadata was recorded.")
        return

    print("\nLLM usage by call:")
    for index, record in enumerate(records, start=1):
        print(
            f"  {index}. {record.call_name} | model={record.model} | "
            f"prompt={record.prompt_tokens} | completion={record.completion_tokens} | "
            f"total={record.total_tokens} | cost_usd={record.cost_usd}"
        )

    summary = summarize_llm_usage()
    print(
        "LLM usage current run total: "
        f"calls={summary['calls']} | "
        f"prompt={summary['prompt_tokens']} | "
        f"completion={summary['completion_tokens']} | "
        f"total={summary['total_tokens']} | "
        f"cost_usd={summary['cost_usd']}"
    )
    ledger_summary = summarize_llm_usage_ledger()
    print(
        "LLM usage local ledger grand total: "
        f"calls={ledger_summary['calls']} | "
        f"prompt={ledger_summary['prompt_tokens']} | "
        f"completion={ledger_summary['completion_tokens']} | "
        f"total={ledger_summary['total_tokens']} | "
        f"cost_usd={ledger_summary['cost_usd']} | "
        f"path={llm_usage_ledger_path()}"
    )
