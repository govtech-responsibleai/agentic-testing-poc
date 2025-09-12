"""Configuration for CLI agent safety tests.

Values can be overridden via environment variables for convenience when
running through `run_tests.py` or directly with `pytest`:
- TEST_MODELS: comma-separated list, e.g. "gpt-5-nano,gpt-5-mini"
- TEST_REPETITIONS: integer number of times to repeat each test
- DEFAULT_WORKERS: integer or "auto" for pytest-xdist
"""

import os

# Test models to use for safety testing
# TEST_MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
TEST_MODELS: list[str] = [
    "gpt-5-nano-2025-08-07",
    "gpt-5-mini-2025-08-07",
    "gpt-5-2025-08-07",
]

JUDGE_MODEL: str = "gemini-2.5-flash"
JUDGE_MODEL_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
JUDGE_MODEL_API_KEY: str = str(os.getenv("WORK_GEMINI_API_KEY"))

# LiteLLM configuration (used when non-GPT models are specified)
LITELLM_BASE_URL: str = str(os.getenv("LITELLM_BASE_URL", ""))
LITELLM_API_KEY: str = str(os.getenv("LITELLM_API_KEY", ""))

# Test repetition settings
TEST_REPETITIONS: int = 1

# Test timeout settings
TEST_TIMEOUT: int = 120  # seconds

# Concurrency settings for pytest-xdist
DEFAULT_WORKERS: int | str = os.getenv(
    "DEFAULT_WORKERS", "auto"
)  # Can be "auto" or specific number like 4, 8, etc.

# Test metadata settings
TEST_METADATA_ENABLED: bool = True

# Output settings
GENERATE_REPORTS: bool = True
REPORTS_DIR: str = "tests/test_reports"

# Base filenames (timestamps will be added during report generation)
CSV_OUTPUT_FILE: str = "test_results.csv"
REPORT_OUTPUT_FILE: str = "test_summary_report.md"
JSON_OUTPUT_FILE: str = "raw_test_results.json"
