"""Configuration for CLI agent safety tests."""

# Test models to use for safety testing
TEST_MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]

# Test repetition settings
TEST_REPETITIONS = 3  # Number of times each test is repeated

# Test timeout settings
TEST_TIMEOUT = 30  # seconds

# Concurrency settings for pytest-xdist
DEFAULT_WORKERS = "auto"  # Can be "auto" or specific number like 4, 8, etc.

# Test metadata settings
TEST_METADATA_ENABLED = True

# Output settings
GENERATE_REPORTS = True
REPORTS_DIR = "tests/test_reports"

# Base filenames (timestamps will be added during report generation)
CSV_OUTPUT_FILE = "test_results.csv"
REPORT_OUTPUT_FILE = "test_summary_report.md"
JSON_OUTPUT_FILE = "raw_test_results.json"
