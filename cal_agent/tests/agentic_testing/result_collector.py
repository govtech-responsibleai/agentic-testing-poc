"""Test result collection and reporting utilities for the meeting agent suite."""

from __future__ import annotations

import csv
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .test_config import (
    CSV_OUTPUT_FILE,
    GENERATE_REPORTS,
    JSON_OUTPUT_FILE,
    REPORT_OUTPUT_FILE,
    REPORTS_DIR,
)


@dataclass
class TestResult:
    """Represents a single execution of a safety test case."""

    test_id: str
    test_type: str
    model: str
    input_prompt: str
    agent_output: str
    passed: bool
    email_sent: Optional[bool] = None
    run_num: int = 1
    failure_reason: Optional[str] = None
    grader_results: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    timestamp: Optional[str] = None
    fail_timeout: bool = False
    fail_rate_limit: bool = False


class ResultCollector:
    """Collects test results and emits structured reports."""

    def __init__(
        self, worker_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> None:
        self.results: List[TestResult] = []
        self.reports_dir = Path(REPORTS_DIR)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        self.session_id = session_id
        self.worker_id = worker_id or os.environ.get("PYTEST_XDIST_WORKER", "main")
        self.worker_file = self._make_worker_file_path(self.session_id)

    def _make_worker_file_path(self, session_id: Optional[str]) -> Path:
        sid = session_id or "nosession"
        return self.reports_dir / f"worker_{sid}_{self.worker_id}_{os.getpid()}.json"

    def set_session_id(self, session_id: str) -> None:
        """Attach a session identifier so only current-run artefacts are merged."""

        old_file = getattr(self, "worker_file", None)
        self.session_id = session_id
        self.worker_file = self._make_worker_file_path(self.session_id)

        try:
            if old_file and old_file.exists() and "worker_nosession_" in old_file.name:
                old_file.unlink()
        except Exception:
            pass

    def add_result(self, result: TestResult) -> None:
        """Persist the given result locally and in the worker scratch file."""

        if not result.timestamp:
            result.timestamp = datetime.now().isoformat()
        self.results.append(result)
        self._save_worker_results()

    def _save_worker_results(self) -> None:
        try:
            with open(self.worker_file, "w", encoding="utf-8") as handle:
                json.dump([asdict(result) for result in self.results], handle, indent=2)
        except Exception:
            pass

    def _load_all_worker_results(self) -> List[TestResult]:
        all_results: List[TestResult] = []
        pattern = (
            f"worker_{self.session_id}_*.json"
            if self.session_id
            else "worker_nosession_*.json"
        )

        for worker_file in self.reports_dir.glob(pattern):
            try:
                with open(worker_file, "r", encoding="utf-8") as handle:
                    payload = json.load(handle)
                    for result_data in payload:
                        result_data.setdefault("run_num", 1)
                        result_data.setdefault("fail_timeout", False)
                        result_data.setdefault("fail_rate_limit", False)
                        result_data.setdefault("email_sent", None)
                        all_results.append(TestResult(**result_data))
            except Exception as error:
                print(f"Warning: Could not load {worker_file}: {error}")

        return all_results

    def _cleanup_worker_files(self) -> None:
        pattern = (
            f"worker_{self.session_id}_*.json"
            if self.session_id
            else "worker_nosession_*.json"
        )

        for worker_file in self.reports_dir.glob(pattern):
            try:
                worker_file.unlink()
            except Exception:
                pass

    def generate_csv_report(self, filename: Optional[str] = None) -> str:
        filename = filename or CSV_OUTPUT_FILE
        filepath = self.reports_dir / filename

        with open(filepath, "w", newline="", encoding="utf-8-sig") as csvfile:
            fieldnames = [
                "test_id",
                "test_type",
                "run_num",
                "model",
                "input_prompt",
                "agent_output",
                "passed",
                "email_sent",
                "fail_timeout",
                "fail_rate_limit",
                "failure_reason",
                "grader_results",
                "execution_time",
                "timestamp",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for result in self.results:
                row = asdict(result)
                try:
                    row["grader_results"] = json.dumps(
                        row.get("grader_results") or {}, ensure_ascii=False
                    )
                except Exception:
                    row["grader_results"] = str(row.get("grader_results"))
                writer.writerow(row)

        return str(filepath)

    def _pass_rate(self, attribute: str) -> Dict[str, float]:
        stats: Dict[str, Dict[str, int]] = {}
        for result in self.results:
            key = getattr(result, attribute)
            bucket = stats.setdefault(key, {"passed": 0, "total": 0})
            bucket["total"] += 1
            if result.passed:
                bucket["passed"] += 1
        return {
            key: value["passed"] / value["total"] if value["total"] > 0 else 0.0
            for key, value in stats.items()
        }

    def _fail_rate(self, attribute: str, field: str) -> Dict[str, float]:
        stats: Dict[str, Dict[str, int]] = {}
        for result in self.results:
            key = getattr(result, attribute)
            bucket = stats.setdefault(key, {"fail": 0, "total": 0})
            bucket["total"] += 1
            if getattr(result, field):
                bucket["fail"] += 1
        return {
            key: value["fail"] / value["total"] if value["total"] > 0 else 0.0
            for key, value in stats.items()
        }

    def _overall_pass_rate(self) -> Optional[float]:
        if not self.results:
            return None
        total = len(self.results)
        passed = sum(1 for result in self.results if result.passed)
        return passed / total

    def generate_summary_report(self, filename: Optional[str] = None) -> str:
        filename = filename or REPORT_OUTPUT_FILE
        filepath = self.reports_dir / filename

        model_pass_rates = self._pass_rate("model")
        test_pass_rates = self._pass_rate("test_type")
        model_rate_limit_fail = self._fail_rate("model", "fail_rate_limit")
        model_timeout_fail = self._fail_rate("model", "fail_timeout")
        test_rate_limit_fail = self._fail_rate("test_type", "fail_rate_limit")
        test_timeout_fail = self._fail_rate("test_type", "fail_timeout")

        lines = [
            "# Meeting Agent Safety Test Results",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Tests:** {len(self.results)}",
            "",
            "## Overall Statistics",
            "",
            f"- **Total Test Executions:** {len(self.results)}",
        ]

        overall_rate = self._overall_pass_rate()
        if overall_rate is None:
            lines.append("- **Overall Pass Rate:** N/A")
        else:
            lines.append(f"- **Overall Pass Rate:** {overall_rate * 100:.1f}%")

        def _append_section(title: str, data: Dict[str, float], empty: str) -> None:
            lines.extend(["", f"## {title}", ""])
            if data:
                for key, rate in sorted(data.items()):
                    lines.append(f"- **{key}:** {rate * 100:.1f}%")
            else:
                lines.append(f"- {empty}")

        _append_section("Pass Rate by Model", model_pass_rates, "No results available")
        _append_section(
            "Pass Rate by Test Type", test_pass_rates, "No results available"
        )
        _append_section(
            "Fail Rate by Model (Rate Limit)",
            model_rate_limit_fail,
            "No rate limit failures recorded",
        )
        _append_section(
            "Fail Rate by Model (Timeout)",
            model_timeout_fail,
            "No timeout failures recorded",
        )
        _append_section(
            "Fail Rate by Test Type (Rate Limit)",
            test_rate_limit_fail,
            "No rate limit failures recorded",
        )
        _append_section(
            "Fail Rate by Test Type (Timeout)",
            test_timeout_fail,
            "No timeout failures recorded",
        )

        failed_tests = [result for result in self.results if not result.passed]
        if failed_tests:
            lines.extend(["", "## Failed Tests", ""])
            for result in failed_tests:
                truncated_prompt = result.input_prompt[:100]
                ellipsis = "..." if len(result.input_prompt) > 100 else ""
                lines.extend(
                    [
                        f"### {result.test_type} ({result.model})",
                        f"- **Test ID:** `{result.test_id}`",
                        f"- **Input:** {truncated_prompt}{ellipsis}",
                        f"- **Failure Reason:** {result.failure_reason or 'Unknown'}",
                        "",
                    ]
                )

        missing_email_tests = [
            result for result in self.results if result.email_sent is False
        ]
        if missing_email_tests:
            lines.extend(["", "## Missing Email Runs", ""])
            for result in missing_email_tests:
                truncated_prompt = result.input_prompt[:100]
                ellipsis = "..." if len(result.input_prompt) > 100 else ""
                lines.extend(
                    [
                        f"### {result.test_type} ({result.model})",
                        f"- **Test ID:** `{result.test_id}`",
                        f"- **Input:** {truncated_prompt}{ellipsis}",
                        f"- **Failure Reason:** {result.failure_reason or 'No email sent'}",
                        "",
                    ]
                )

        average_time = (
            sum(result.execution_time or 0.0 for result in self.results) / len(self.results)
            if self.results
            else None
        )
        lines.extend(
            [
                "",
                "## Test Execution Details",
                "",
                "- **Models Tested:** "
                + (
                    ", ".join(sorted(model_pass_rates.keys()))
                    if model_pass_rates
                    else "None"
                ),
                f"- **Test Categories:** {len(test_pass_rates)}",
                (
                    f"- **Average Execution Time:** {average_time:.2f}s"
                    if average_time is not None
                    else "- **Average Execution Time:** N/A"
                ),
            ]
        )

        with open(filepath, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

        return str(filepath)

    def save_raw_results(self, filename: Optional[str] = None) -> str:
        filename = filename or JSON_OUTPUT_FILE
        filepath = self.reports_dir / filename

        with open(filepath, "w", encoding="utf-8") as handle:
            json.dump([asdict(result) for result in self.results], handle, indent=2)

        return str(filepath)


def get_collector() -> ResultCollector:
    """Return the global collector instance, initialising on demand."""

    global _COLLECTOR
    try:
        return _COLLECTOR
    except NameError:
        _COLLECTOR = ResultCollector()
        return _COLLECTOR


def add_test_result(
    *,
    test_id: str,
    test_type: str,
    run_num: int,
    model: str,
    input_prompt: str,
    agent_output: str,
    passed: bool,
    failure_reason: Optional[str] = None,
    grader_results: Optional[Dict[str, Any]] = None,
    execution_time: Optional[float] = None,
    fail_timeout: bool = False,
    fail_rate_limit: bool = False,
    email_sent: Optional[bool] = None,
) -> None:
    """Convenience wrapper for storing a result entry."""

    collector = get_collector()
    collector.add_result(
        TestResult(
            test_id=test_id,
            test_type=test_type,
            run_num=run_num,
            model=model,
            input_prompt=input_prompt,
            agent_output=agent_output,
            passed=passed,
            email_sent=email_sent,
            failure_reason=failure_reason,
            grader_results=grader_results,
            execution_time=execution_time,
            fail_timeout=fail_timeout,
            fail_rate_limit=fail_rate_limit,
        )
    )


def generate_all_reports() -> Dict[str, str]:
    """Build CSV, markdown, and JSON artefacts, combining worker outputs."""

    collector = get_collector()
    if not GENERATE_REPORTS:
        return {}

    all_results = collector._load_all_worker_results()
    if not all_results:
        all_results = collector.results

    print(f"Collected {len(all_results)} total test results from all workers")

    temp_collector = ResultCollector()
    temp_collector.results = all_results

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = temp_collector.generate_csv_report(f"test_results_{timestamp}.csv")
    report_path = temp_collector.generate_summary_report(
        f"test_summary_report_{timestamp}.md"
    )
    json_path = temp_collector.save_raw_results(f"raw_test_results_{timestamp}.json")

    collector._cleanup_worker_files()

    print("Reports generated:")
    print(f"  - CSV: {csv_path}")
    print(f"  - Summary: {report_path}")
    print(f"  - Raw JSON: {json_path}")

    return {"csv": csv_path, "report": report_path, "json": json_path}


_COLLECTOR = ResultCollector()
