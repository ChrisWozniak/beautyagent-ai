"""Run the Week 2 backend pre-demo validation sequence.

Run from the repository root:

    python backend/scripts/run_demo_smoke.py

This intentionally runs the live Sonnet brand voice calibration set unless
`--skip-live-brand-voice` is passed.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class SmokeStep:
    name: str
    command: list[str]
    spends_llm_tokens: bool = False


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Week 2 backend checks before demo or frontend integration.",
    )
    parser.add_argument(
        "--skip-live-brand-voice",
        action="store_true",
        help="Skip the live Sonnet brand voice calibration step.",
    )
    return parser.parse_args(argv)


def build_steps(skip_live_brand_voice: bool = False) -> list[SmokeStep]:
    steps = [
        SmokeStep(
            name="Backend unit tests",
            command=[
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                "backend\\tests",
                "-v",
            ],
        ),
        SmokeStep(
            name="Token-safe red-team compliance eval",
            command=[
                sys.executable,
                "backend/scripts/run_red_team_eval.py",
                "--mock-brand-voice",
                "--compact",
            ],
        ),
    ]

    if not skip_live_brand_voice:
        steps.append(
            SmokeStep(
                name="Live Sonnet brand voice calibration eval",
                command=[
                    sys.executable,
                    "backend/scripts/run_brand_voice_eval.py",
                    "--compact",
                ],
                spends_llm_tokens=True,
            )
        )

    return steps


def _format_command(command: list[str]) -> str:
    return " ".join(command)


def run_step(step: SmokeStep) -> int:
    print(f"\n=== {step.name} ===")
    if step.spends_llm_tokens:
        print("This step intentionally spends a small number of Claude/Sonnet tokens.")
    print(_format_command(step.command))
    completed = subprocess.run(step.command, cwd=ROOT)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    steps = build_steps(skip_live_brand_voice=args.skip_live_brand_voice)

    print("Week 2 backend demo smoke starting.")
    for step in steps:
        exit_code = run_step(step)
        if exit_code != 0:
            print(f"\nDemo smoke failed at: {step.name}")
            return exit_code

    print("\nWeek 2 backend demo smoke passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
