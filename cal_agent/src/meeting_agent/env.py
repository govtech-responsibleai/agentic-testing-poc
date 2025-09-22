"""Utilities for loading environment variables from `.env` files."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

_COMMENT_CHAR = "#"


def _iter_env_lines(env_path: Path) -> Iterator[tuple[str, str]]:
    """Yield key and value pairs parsed from the provided env file."""

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith(_COMMENT_CHAR):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        parsed_key = key.strip()
        if not parsed_key:
            continue
        parsed_value = value.strip().strip('\"').strip("'")
        yield parsed_key, parsed_value


def load_env(env_path: Path | None = None) -> None:
    """Populate environment variables from the given `.env` file.

    Existing environment variables take precedence over entries defined in the
    file to avoid unintentionally overriding values provided by the user.
    """

    default_root = Path(__file__).resolve().parents[2]
    path = env_path or default_root / ".env"
    if not path.exists():
        return
    for key, value in _iter_env_lines(path):
        os.environ.setdefault(key, value)
