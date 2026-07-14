"""Shared JSON config loading helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class ConfigLoadError(RuntimeError):
    """Raised when a required backend JSON config file cannot be loaded."""


def load_json_config(path: Path, label: str) -> Any:
    try:
        with path.open(encoding="utf-8") as config_file:
            return json.load(config_file)
    except FileNotFoundError as exc:
        raise ConfigLoadError(f"{label} config file was not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigLoadError(
            f"{label} config file contains invalid JSON at line {exc.lineno}, "
            f"column {exc.colno}: {path}"
        ) from exc
    except OSError as exc:
        raise ConfigLoadError(f"{label} config file could not be read: {path}") from exc
