"""Unit tests for the result collector reporting helpers."""

from __future__ import annotations

import os
from pathlib import Path

from .pytest_plugin import _classify_failure_reason
from .result_collector import ResultCollector, TestResult


os.environ.setdefault("OPENAI_API_KEY", "test-key")
os.environ.setdefault("WORK_GEMINI_API_KEY", "test-key")


def test_generate_csv_report_includes_fail_no_cal(tmp_path: Path) -> None:
    """Ensure the CSV report records the no-calendar failure flag."""

    collector = ResultCollector()
    collector.reports_dir = tmp_path
    collector.set_session_id("unit-test")

    collector.add_result(
        TestResult(
            test_id="test-1",
            test_type="dummy",
            run_num=1,
            model="model-x",
            input_prompt="prompt",
            agent_output="output",
            passed=False,
            fail_no_cal=True,
        )
    )

    csv_path = Path(collector.generate_csv_report("results.csv"))
    lines = csv_path.read_text(encoding="utf-8-sig").splitlines()
    header = lines[0].split(",")
    assert "fail_no_cal" in header
    assert "email_sent" in header

    values = lines[1].split(",")
    fail_no_cal_index = header.index("fail_no_cal")
    assert values[fail_no_cal_index].lower() == "true"
    email_sent_index = header.index("email_sent")
    assert values[email_sent_index].lower() == "false"


def test_classify_failure_reason_usage_limit_counts_timeout() -> None:
    message = (
        "pydantic_ai.exceptions.UsageLimitExceeded: The next request would exceed "
        "the request_limit of 50"
    )
    fail_timeout, fail_rate_limit, fail_no_cal = _classify_failure_reason(message)
    assert fail_timeout is True
    assert fail_rate_limit is False
    assert fail_no_cal is False
