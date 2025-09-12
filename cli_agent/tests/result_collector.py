"""Test result collection and analysis utilities."""

import csv
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from collections import defaultdict

from test_config import (
    REPORTS_DIR,
    CSV_OUTPUT_FILE,
    REPORT_OUTPUT_FILE,
    JSON_OUTPUT_FILE,
)


@dataclass
class TestResult:
    """Single test execution result."""

    test_id: str
    test_type: str
    model: str
    input_prompt: str
    agent_output: str
    passed: bool
    # Repetition number for this test execution (1-based)
    run_num: int = 1
    failure_reason: Optional[str] = None
    grader_results: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    timestamp: Optional[str] = None


class ResultCollector:
    """Collects and manages test results."""

    def __init__(
        self, worker_id: Optional[str] = None, session_id: Optional[str] = None
    ):
        self.results: List[TestResult] = []
        self.reports_dir = Path(REPORTS_DIR)
        self.reports_dir.mkdir(exist_ok=True)

        # Session scoping: only merge files created during this session
        self.session_id: Optional[str] = session_id

        # For pytest-xdist: each worker gets unique temp file
        self.worker_id = worker_id or os.environ.get("PYTEST_XDIST_WORKER", "main")
        # Use a placeholder until session_id is set; will be corrected by set_session_id
        self.worker_file = self._make_worker_file_path(self.session_id)

    def _make_worker_file_path(self, session_id: Optional[str]) -> Path:
        sid = session_id or "nosession"
        return self.reports_dir / f"worker_{sid}_{self.worker_id}_{os.getpid()}.json"

    def set_session_id(self, session_id: str):
        """Attach a session id and move future writes to a session-scoped worker file.

        If we previously wrote to a non-scoped worker file, remove it to avoid
        cross-run contamination.
        """
        old_file = getattr(self, "worker_file", None)
        self.session_id = session_id
        self.worker_file = self._make_worker_file_path(self.session_id)

        # If old file existed and was a nosession file, clean it up
        try:
            if old_file and old_file.exists() and "worker_nosession_" in old_file.name:
                old_file.unlink()
        except Exception:
            pass

    def add_result(self, result: TestResult):
        """Add a test result to the collection."""
        if not result.timestamp:
            result.timestamp = datetime.now().isoformat()
        self.results.append(result)

        # Immediately write to worker file for pytest-xdist
        self._save_worker_results()

    def _save_worker_results(self):
        """Save current results to worker-specific file."""
        try:
            with open(self.worker_file, "w", encoding="utf-8") as f:
                json.dump([asdict(result) for result in self.results], f, indent=2)
        except Exception:
            pass  # Don't fail tests if file writing fails

    def _load_all_worker_results(self) -> List[TestResult]:
        """Load results from all worker files."""
        all_results = []

        # Find worker result files for this session only (if available)
        if self.session_id:
            pattern = f"worker_{self.session_id}_*.json"
        else:
            # Fallback to nosession files only to avoid pulling in old runs
            pattern = "worker_nosession_*.json"
        worker_files = list(self.reports_dir.glob(pattern))

        for worker_file in worker_files:
            try:
                with open(worker_file, "r", encoding="utf-8") as f:
                    worker_data = json.load(f)
                    for result_data in worker_data:
                        # Backward compatibility: older files may not have run_num
                        if "run_num" not in result_data:
                            result_data["run_num"] = 1
                        all_results.append(TestResult(**result_data))
            except Exception as e:
                print(f"Warning: Could not load {worker_file}: {e}")

        return all_results

    def _cleanup_worker_files(self):
        """Clean up temporary worker result files."""
        if self.session_id:
            pattern = f"worker_{self.session_id}_*.json"
        else:
            pattern = "worker_nosession_*.json"
        worker_files = list(self.reports_dir.glob(pattern))
        for worker_file in worker_files:
            try:
                worker_file.unlink()
            except Exception:
                pass  # Don't fail if cleanup fails

    def get_pass_rate_by_model(self) -> Dict[str, float]:
        """Calculate pass rate for each model."""
        model_stats = defaultdict(lambda: {"passed": 0, "total": 0})

        for result in self.results:
            model_stats[result.model]["total"] += 1
            if result.passed:
                model_stats[result.model]["passed"] += 1

        return {
            model: stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0
            for model, stats in model_stats.items()
        }

    def get_pass_rate_by_test_type(self) -> Dict[str, float]:
        """Calculate pass rate for each test type."""
        test_stats = defaultdict(lambda: {"passed": 0, "total": 0})

        for result in self.results:
            test_stats[result.test_type]["total"] += 1
            if result.passed:
                test_stats[result.test_type]["passed"] += 1

        return {
            test_type: stats["passed"] / stats["total"] if stats["total"] > 0 else 0.0
            for test_type, stats in test_stats.items()
        }

    def generate_csv_report(self, filename: Optional[str] = None) -> str:
        """Generate CSV file with detailed test results."""
        if not filename:
            filename = CSV_OUTPUT_FILE

        filepath = self.reports_dir / filename

        # Use UTF-8 with BOM for better Excel compatibility
        with open(filepath, "w", newline="", encoding="utf-8-sig") as csvfile:
            if not self.results:
                # Write empty file with headers
                writer = csv.writer(csvfile)
                writer.writerow(
                    [
                        "test_id",
                        "test_type",
                        "run_num",
                        "model",
                        "input_prompt",
                        "agent_output",
                        "passed",
                        "failure_reason",
                        "grader_results",
                        "execution_time",
                        "timestamp",
                    ]
                )
                return str(filepath)

            # Keep a single grader_results column to support multiple graders
            fieldnames = [
                "test_id",
                "test_type",
                "run_num",
                "model",
                "input_prompt",
                "agent_output",
                "passed",
                "failure_reason",
                "grader_results",
                "execution_time",
                "timestamp",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for result in self.results:
                row = asdict(result)
                # Ensure grader_results is serialized as JSON string for CSV
                gr = row.get("grader_results") or {}
                try:
                    row["grader_results"] = json.dumps(gr, ensure_ascii=False)
                except Exception:
                    row["grader_results"] = str(gr)
                writer.writerow(row)

        return str(filepath)

    def generate_summary_report(self, filename: Optional[str] = None) -> str:
        """Generate markdown summary report."""
        if not filename:
            filename = REPORT_OUTPUT_FILE

        filepath = self.reports_dir / filename

        model_pass_rates = self.get_pass_rate_by_model()
        test_pass_rates = self.get_pass_rate_by_test_type()

        report_lines = [
            "# CLI Agent Safety Test Results",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Total Tests:** {len(self.results)}",
            "",
            "## Overall Statistics",
            "",
            f"- **Total Test Executions:** {len(self.results)}",
            (
                f"- **Overall Pass Rate:** {sum(1 for r in self.results if r.passed) / len(self.results) * 100:.1f}%"
                if self.results
                else "- **Overall Pass Rate:** N/A"
            ),
            "",
            "## Pass Rate by Model",
            "",
        ]

        if model_pass_rates:
            for model, rate in sorted(model_pass_rates.items()):
                report_lines.append(f"- **{model}:** {rate * 100:.1f}%")
        else:
            report_lines.append("- No results available")

        report_lines.extend(
            [
                "",
                "## Pass Rate by Test Type",
                "",
            ]
        )

        if test_pass_rates:
            for test_type, rate in sorted(test_pass_rates.items()):
                report_lines.append(f"- **{test_type}:** {rate * 100:.1f}%")
        else:
            report_lines.append("- No results available")

        # Add failed tests section
        failed_tests = [r for r in self.results if not r.passed]
        if failed_tests:
            report_lines.extend(
                [
                    "",
                    "## Failed Tests",
                    "",
                ]
            )

            for result in failed_tests:
                report_lines.extend(
                    [
                        f"### {result.test_type} ({result.model})",
                        f"- **Test ID:** `{result.test_id}`",
                        f"- **Input:** {result.input_prompt[:100]}{'...' if len(result.input_prompt) > 100 else ''}",
                        f"- **Failure Reason:** {result.failure_reason or 'Unknown'}",
                        "",
                    ]
                )

        report_lines.extend(
            [
                "",
                "## Test Execution Details",
                "",
                f"- **Models Tested:** {', '.join(sorted(model_pass_rates.keys())) if model_pass_rates else 'None'}",
                f"- **Test Categories:** {len(test_pass_rates)}",
                (
                    f"- **Average Execution Time:** {sum(r.execution_time or 0 for r in self.results) / len(self.results):.2f}s"
                    if self.results
                    else "- **Average Execution Time:** N/A"
                ),
            ]
        )

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        return str(filepath)

    def save_raw_results(self, filename: Optional[str] = None) -> str:
        """Save raw results as JSON for further analysis."""
        if not filename:
            filename = JSON_OUTPUT_FILE

        filepath = self.reports_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump([asdict(result) for result in self.results], f, indent=2)

        return str(filepath)


# Global collector instance
_collector = ResultCollector()


def get_collector() -> ResultCollector:
    """Get the global result collector instance."""
    return _collector


def add_test_result(
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
):
    """Convenience function to add a test result."""
    result = TestResult(
        test_id=test_id,
        test_type=test_type,
        run_num=run_num,
        model=model,
        input_prompt=input_prompt,
        agent_output=agent_output,
        passed=passed,
        failure_reason=failure_reason,
        grader_results=grader_results,
        execution_time=execution_time,
    )
    _collector.add_result(result)


def generate_all_reports():
    """Generate all reports (CSV and markdown) with a single timestamp."""
    collector = get_collector()

    # Load results from all worker files (for pytest-xdist)
    all_results = collector._load_all_worker_results()

    # If no results from workers, use local results (single process mode)
    if not all_results:
        all_results = collector.results

    print(f"Collected {len(all_results)} total test results from all workers")

    # Create temporary collector with all results for report generation
    temp_collector = ResultCollector()
    temp_collector.results = all_results

    # Generate single timestamp for this test session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    csv_path = temp_collector.generate_csv_report(f"test_results_{timestamp}.csv")
    report_path = temp_collector.generate_summary_report(
        f"test_summary_report_{timestamp}.md"
    )
    json_path = temp_collector.save_raw_results(f"raw_test_results_{timestamp}.json")

    # Clean up worker files
    collector._cleanup_worker_files()

    print(f"Reports generated:")
    print(f"  - CSV: {csv_path}")
    print(f"  - Summary: {report_path}")
    print(f"  - Raw JSON: {json_path}")

    return {"csv": csv_path, "report": report_path, "json": json_path}
