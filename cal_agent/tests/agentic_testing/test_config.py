"""Configuration helpers for meeting agent safety tests."""
from __future__ import annotations

import os
from typing import List

DEFAULT_MODEL: str = "openai:gpt-5-mini-2025-08-07"

_ENV_MODELS = os.getenv("CAL_AGENT_TEST_MODELS")
if _ENV_MODELS:
    TEST_MODELS: List[str] = [
        model.strip() for model in _ENV_MODELS.split(",") if model.strip()
    ]
else:
    TEST_MODELS = [DEFAULT_MODEL]

TEST_REPETITIONS: int = int(os.getenv("CAL_AGENT_TEST_REPETITIONS", "1"))

JUDGE_MODEL: str = os.getenv("CAL_AGENT_JUDGE_MODEL", "gemini-2.5-flash")
JUDGE_MODEL_BASE_URL: str = os.getenv(
    "CAL_AGENT_JUDGE_MODEL_BASE_URL",
    "https://generativelanguage.googleapis.com/v1beta/openai/",
)
JUDGE_MODEL_API_KEY: str = os.getenv("WORK_GEMINI_API_KEY", "")
