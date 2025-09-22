"""Configuration helpers for meeting agent safety tests."""
from __future__ import annotations

import os
from pathlib import Path
from typing import List


def _env_flag(name: str, default: bool) -> bool:
    """Return the boolean value encoded in an environment variable."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


_ENV_MODELS = os.getenv("CAL_AGENT_TEST_MODELS")
if _ENV_MODELS:
    TEST_MODELS: List[str] = [
        model.strip() for model in _ENV_MODELS.split(",") if model.strip()
    ]
else:
    TEST_MODELS = [
        "gpt-5-nano-2025-08-07",
        "gpt-5-mini-2025-08-07",
        "gpt-5-2025-08-07",
        "gemini-2.5-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-pro",
        "apac.anthropic.claude-sonnet-4-20250514-v1:0",
        "us.anthropic.claude-opus-4-1-20250805-v1:0",
        "zai-org/GLM-4.5:fireworks-ai",
        "deepseek-ai/DeepSeek-V3.1:novita",
        # "Qwen/Qwen3-235B-A22B-Instruct-2507:cerebras",
        "moonshotai/Kimi-K2-Instruct-0905:together",
    ]

TEST_REPETITIONS: int = int(os.getenv("CAL_AGENT_TEST_REPETITIONS", "1"))

JUDGE_MODEL: str = os.getenv("CAL_AGENT_JUDGE_MODEL", "gemini-2.5-flash")
JUDGE_MODEL_BASE_URL: str = os.getenv(
    "CAL_AGENT_JUDGE_MODEL_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
)
JUDGE_MODEL_API_KEY: str = os.getenv("WORK_GEMINI_API_KEY", "")


_BASE_DIR = Path(__file__).resolve().parent

GENERATE_REPORTS: bool = _env_flag("CAL_AGENT_GENERATE_REPORTS", True)
REPORTS_DIR: str = os.getenv(
    "CAL_AGENT_REPORTS_DIR",
    str(_BASE_DIR / "test_reports"),
)
CSV_OUTPUT_FILE: str = os.getenv("CAL_AGENT_CSV_OUTPUT_FILE", "test_results.csv")
REPORT_OUTPUT_FILE: str = os.getenv(
    "CAL_AGENT_REPORT_OUTPUT_FILE",
    "test_summary_report.md",
)
JSON_OUTPUT_FILE: str = os.getenv(
    "CAL_AGENT_JSON_OUTPUT_FILE",
    "raw_test_results.json",
)
