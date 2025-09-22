"""Pytest configuration for meeting agent safety regression tests."""
from __future__ import annotations

pytest_plugins = [
    "cal_agent.tests.agentic_testing.pytest_plugin",
    "cal_agent.tests.agentic_testing.data.test_cases",
]
