"""
Utility functions for agentic testing.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from bs4 import BeautifulSoup


def setup_logging(test_name: str = "agentic_test") -> logging.Logger:
    """Set up logging for test runs with file and console output."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = Path("tests/agentic_testing/logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    
    log_file = log_dir / f"{test_name}_{timestamp}.log"
    
    # Configure file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.INFO)
    
    # Configure console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Create formatter with timestamps
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Get logger
    logger = logging.getLogger(test_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()  # Clear any existing handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def read_html_file(html_path: str, base_path: Path = None) -> str:
    """
    Read and parse HTML file to extract text content.
    
    Args:
        html_path: Relative path to HTML file
        base_path: Base directory for HTML files (default: tests/agentic_testing/data)
    
    Returns:
        Extracted text content from HTML, limited to 5000 chars
    """
    if base_path is None:
        base_path = Path("tests/agentic_testing/data")
    
    full_path = base_path / html_path
    
    if not full_path.exists():
        return "Page not found"
    
    with open(full_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Parse HTML to extract text
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text
    text = soup.get_text()
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text[:5000]  # Limit to 5000 chars


def save_test_report(
    test_id: str,
    test_report: Dict[str, Any],
    report_dir: Path = None
) -> Path:
    """
    Save test report to JSON file.
    
    Args:
        test_id: Test identifier
        test_report: Report data to save
        report_dir: Directory for reports (default: tests/agentic_testing/logs)
    
    Returns:
        Path to saved report file
    """
    if report_dir is None:
        report_dir = Path("tests/agentic_testing/logs")
    
    report_dir.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"test_report_{test_id}_{timestamp}.json"
    
    with open(report_path, 'w') as f:
        json.dump(test_report, f, indent=2)
    
    return report_path


def log_section_header(logger: logging.Logger, title: str, level: str = "="):
    """
    Log a formatted section header.
    
    Args:
        logger: Logger instance
        title: Section title
        level: Character to use for separator line
    """
    separator = level * 60
    logger.info("")
    logger.info(separator)
    logger.info(title)
    logger.info(separator)


def log_metric_result(
    logger: logging.Logger,
    metric_name: str,
    passed: bool,
    details: str = None
):
    """
    Log a metric result with appropriate formatting.
    
    Args:
        logger: Logger instance
        metric_name: Name of the metric
        passed: Whether the metric passed
        details: Optional additional details
    """
    icon = "✅" if passed else "❌"
    status = "PASSED" if passed else "FAILED"
    
    logger.info(f"{icon} {metric_name}: {status}")
    if details:
        logger.info(f"   {details}")