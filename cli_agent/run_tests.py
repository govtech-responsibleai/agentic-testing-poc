#!/usr/bin/env python3
"""
CLI Agent Safety Test Runner

This script runs the safety tests and generates comprehensive reports.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from tests.test_config import TEST_MODELS, TEST_REPETITIONS, DEFAULT_WORKERS
from tests.result_collector import generate_all_reports


def main():
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

    args = parser.parse_args()

    # Build pytest command
    cmd = ["python", "-m", "pytest", f"tests/{args.test_pattern}"]

    # Add verbosity
    if args.verbose and not args.quick:
        cmd.append("-v")
    elif args.quick:
        cmd.extend(["--tb=no", "-q"])
    else:
        cmd.append("-v")

    # Add workers for parallel execution
    if args.workers != "1":
        cmd.extend(["-n", str(args.workers)])

    # Set environment variables for test configuration
    import os

    env = os.environ.copy()
    env["TEST_MODELS"] = ",".join(args.models)
    env["TEST_REPETITIONS"] = str(args.repetitions)

    print(f"Running CLI agent safety tests...")
    print(f"Models: {args.models}")
    print(f"Repetitions per test: {args.repetitions}")
    print(f"Workers: {args.workers}")
    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    try:
        # Run the tests
        result = subprocess.run(cmd, env=env, check=False)

        print("-" * 60)
        print(f"Tests completed with exit code: {result.returncode}")

        if not args.no_reports:
            print("\nGenerating reports...")
            try:
                paths = generate_all_reports()
                print("✓ Reports generated successfully!")
                print("  Files created:")
                for report_type, path in paths.items():
                    print(f"    {report_type.upper()}: {path}")
            except Exception as e:
                print(f"✗ Error generating reports: {e}")
                return 1

        return result.returncode

    except KeyboardInterrupt:
        print("\nTest execution interrupted by user")
        return 1
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
