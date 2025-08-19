"""
Pytest configuration for agentic testing.
Registers hooks for saving test results.
"""

# Import the hook and results from test file
from tests.agentic_testing.test_websearch_agent import pytest_sessionfinish

# The hook will be automatically registered by pytest when it finds it in conftest.py