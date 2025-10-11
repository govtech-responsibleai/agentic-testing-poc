#!/usr/bin/env python3
"""CLI Agent safety test runner with optional report generation."""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys

from tests.result_collector import generate_all_reports
from tests.test_config import DEFAULT_WORKERS, TEST_MODELS, TEST_REPETITIONS


logger = logging.getLogger(__name__)


def _build_pytest_command(args: argparse.Namespace) -> list[str]:
    """Construct the pytest command based on CLI options."""

    cmd = ["python", "-m", "pytest", f"tests/{args.test_pattern}"]
    if args.verbose and not args.quick:
        cmd.append("-v")
    elif args.quick:
        cmd.extend(["--tb=no", "-q"])
    else:
        cmd.append("-v")

    if args.workers != "1":
        cmd.extend(["-n", str(args.workers)])

    return cmd


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, execute pytest, and optionally generate reports."""

    parser = argparse.ArgumentParser(
        description="Run CLI agent safety tests and generate reports"
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=TEST_MODELS,
        help=f"Models to test (default: {TEST_MODELS})",
    )
    parser.add_argument(
        "--repetitions",
        type=int,
        default=TEST_REPETITIONS,
        help=f"Number of repetitions per test (default: {TEST_REPETITIONS})",
    )
    parser.add_argument(
        "--workers",
        default=DEFAULT_WORKERS,
        help=f"Number of pytest workers (default: {DEFAULT_WORKERS})",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--quick", action="store_true", help="Quick run with less verbose output"
    )
    parser.add_argument(
        "--test-pattern",
        default="test_cli_agent.py",
        help="Test file pattern to run (default: test_cli_agent.py)",
    )
    parser.add_argument(
        "--no-reports", action="store_true", help="Skip report generation"
    )

    args = parser.parse_args(argv)

    cmd = _build_pytest_command(args)
    env = os.environ.copy()
    env["TEST_MODELS"] = ",".join(args.models)
    env["TEST_REPETITIONS"] = str(args.repetitions)

    logger.info("Running CLI agent safety tests")
    logger.info("Models: %s", args.models)
    logger.info("Repetitions per test: %s", args.repetitions)
    logger.info("Workers: %s", args.workers)
    logger.info("Command: %s", " ".join(cmd))

    try:
        result = subprocess.run(cmd, env=env, check=False)
        logger.info("Tests completed with exit code %s", result.returncode)

        if not args.no_reports:
            logger.info("Generating reports...")
            try:
                paths = generate_all_reports()
                for report_type, path in paths.items():
                    logger.info("%s report generated at %s", report_type.upper(), path)
            except Exception:  # noqa: BLE001 - surfaced to user via log
                logger.exception("Error generating reports")
                return 1

        return result.returncode

    except KeyboardInterrupt:
        logger.warning("Test execution interrupted by user")
        return 1
    except Exception:  # noqa: BLE001 - surface unexpected errors
        logger.exception("Unexpected error running tests")
        return 1


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    sys.exit(main())
