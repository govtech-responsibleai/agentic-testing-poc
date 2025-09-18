"""Tests for project environment loading utilities."""
from __future__ import annotations

import os
from pathlib import Path

from meeting_agent.env import load_env


def _snapshot_environment() -> dict[str, str]:
    """Return a copy of the current process environment."""

    return dict(os.environ)


def _restore_environment(snapshot: dict[str, str]) -> None:
    """Restore the process environment from `snapshot`."""

    os.environ.clear()
    os.environ.update(snapshot)


def test_load_env_sets_missing_values(tmp_path: Path) -> None:
    """Load variables defined in the env file when not already set."""

    snapshot = _snapshot_environment()
    try:
        env_path = tmp_path / ".env"
        env_path.write_text("OPENAI_API_KEY=test-key\nOTHER=value\n")
        os.environ.pop("OPENAI_API_KEY", None)
        load_env(env_path=env_path)
        assert os.environ.get("OPENAI_API_KEY") == "test-key"
        assert os.environ.get("OTHER") == "value"
    finally:
        _restore_environment(snapshot)


def test_existing_environment_not_overwritten(tmp_path: Path) -> None:
    """Existing environment variable values take precedence."""

    snapshot = _snapshot_environment()
    try:
        env_path = tmp_path / ".env"
        env_path.write_text("OPENAI_API_KEY=new-key\n")
        os.environ["OPENAI_API_KEY"] = "existing"
        load_env(env_path=env_path)
        assert os.environ.get("OPENAI_API_KEY") == "existing"
    finally:
        _restore_environment(snapshot)


def test_comments_and_whitespace_are_ignored(tmp_path: Path) -> None:
    """Ignore comment lines and parse simple quoted values."""

    snapshot = _snapshot_environment()
    try:
        env_path = tmp_path / ".env"
        env_path.write_text("# comment\n QUOTED='value with spaces' \nEMPTY=\n")
        load_env(env_path=env_path)
        assert os.environ.get("QUOTED") == "value with spaces"
        assert os.environ.get("EMPTY") == ""
    finally:
        _restore_environment(snapshot)
