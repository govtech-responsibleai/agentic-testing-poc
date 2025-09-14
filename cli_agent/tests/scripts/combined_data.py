#!/usr/bin/env python3
"""Merge test result CSVs and renumber run_num.

This script scans for CSV files matching `test_results_*.csv` in a given
reports directory, merges them, and updates `run_num` to be a running count
per unique combination of (test_type, model, input_prompt), ordered by
`timestamp` ascending.

Usage:
  - Default: run with no args to read from `tests/test_reports/` and write to
    `tests/test_reports/test_results_combined.csv`.
  - Custom: `combined_data --reports-dir tests/test_reports --out path/to/out.csv`

Notes:
  - Input CSVs are expected to be encoded as UTF-8 with BOM (utf-8-sig).
  - Output CSV is written as UTF-8 with BOM for Excel compatibility.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple


LOGGER = logging.getLogger(__name__)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments.

    Args:
        argv: Optional sequence of arguments. If None, uses sys.argv.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Merge test result CSVs and renumber run_num per "
            "(test_type, model, input_prompt)."
        )
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("tests/test_reports"),
        help="Directory containing input CSVs (test_results_*.csv).",
    )
    parser.add_argument(
        "--pattern",
        type=str,
        default="test_results_*.csv",
        help="Glob pattern for input CSVs within reports-dir.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("tests/test_reports/test_results_combined.csv"),
        help="Output CSV file path.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging output.",
    )
    return parser.parse_args(argv)


def find_input_files(reports_dir: Path, pattern: str) -> List[Path]:
    """Find input CSV files matching the provided pattern.

    Args:
        reports_dir: Directory to scan.
        pattern: Glob pattern (e.g., 'test_results_*.csv').

    Returns:
        List of matching file paths, sorted by name.
    """
    files = sorted(reports_dir.glob(pattern))
    LOGGER.info("Found %d input CSV files", len(files))
    for f in files:
        LOGGER.debug("Input file: %s", f)
    return files


def read_csv_rows(paths: Iterable[Path]) -> Tuple[List[str], List[Dict[str, str]]]:
    """Read rows from CSV files.

    Args:
        paths: Iterable of CSV file paths.

    Returns:
        A tuple of (fieldnames, rows) where rows are dicts keyed by column names.

    Raises:
        ValueError: If no input files are provided or headers are inconsistent.
    """
    rows: List[Dict[str, str]] = []
    header: List[str] | None = None

    # Increase CSV field size limit to handle large JSON cells.
    try:
        csv.field_size_limit(sys.maxsize)
    except (OverflowError, ValueError):  # pragma: no cover - platform-specific
        csv.field_size_limit(10**7)

    for path in paths:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if header is None:
                header = list(reader.fieldnames or [])
                LOGGER.debug("Detected header: %s", header)
            else:
                other = list(reader.fieldnames or [])
                if other != header:
                    raise ValueError(
                        f"Header mismatch in {path}: {other} != {header}"
                    )
            for row in reader:
                rows.append(row)
    if header is None:
        raise ValueError("No input files or empty CSVs provided.")
    LOGGER.info("Read %d total rows", len(rows))
    return header, rows


def sort_rows_by_timestamp(rows: List[Dict[str, str]]) -> None:
    """Sort rows in place by their ISO 8601 'timestamp' ascending.

    Args:
        rows: Mutable list of row dicts to sort.
    """
    def to_dt(value: str) -> datetime:
        # Handle common ISO 8601 formats; assume naive if no timezone.
        # fromisoformat handles 'YYYY-MM-DDTHH:MM:SS[.ffffff]'.
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            LOGGER.debug("Falling back to raw string sort for timestamp: %s", value)
            # In worst case, return min to avoid crash; sorting will then rely on string comparison.
            return datetime.min

    rows.sort(key=lambda r: to_dt(r.get("timestamp", "")))


def renumber_run_num(rows: List[Dict[str, str]]) -> None:
    """Update 'run_num' to be a running count per (test_type, model, input_prompt).

    The function mutates the provided rows list in-place.

    Args:
        rows: List of row dicts.
    """
    counters: Dict[Tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        key = (
            row.get("test_type", ""),
            row.get("model", ""),
            row.get("input_prompt", ""),
        )
        counters[key] += 1
        row["run_num"] = str(counters[key])


def write_csv(path: Path, header: Sequence[str], rows: Iterable[Dict[str, str]]) -> None:
    """Write rows to a CSV file with UTF-8 BOM encoding.

    Args:
        path: Output file path.
        header: Column names to write as header.
        rows: Iterable of row dicts to write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(header))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    LOGGER.info("Wrote merged CSV: %s", path)


def configure_logging(verbose: bool) -> None:
    """Configure basic logging level and format.

    Args:
        verbose: If True, set level to DEBUG; else INFO.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the merger script.

    Args:
        argv: Optional arguments sequence.

    Returns:
        Process exit code (0 on success, 1 on failure).
    """
    args = parse_args(argv)
    configure_logging(args.verbose)

    try:
        files = find_input_files(args.reports_dir, args.pattern)
        if not files:
            LOGGER.error(
                "No input files found in %s matching %s",
                args.reports_dir,
                args.pattern,
            )
            return 1

        header, rows = read_csv_rows(files)

        # Ensure required columns exist
        required_cols = {"test_type", "model", "input_prompt", "run_num", "timestamp"}
        missing = required_cols - set(header)
        if missing:
            raise ValueError(f"Missing required columns in CSV: {sorted(missing)}")

        sort_rows_by_timestamp(rows)
        renumber_run_num(rows)
        write_csv(args.out, header, rows)
        return 0
    except Exception as exc:  # noqa: BLE001
        LOGGER.exception("Failed to merge CSVs: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
