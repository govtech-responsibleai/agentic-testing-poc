"""Pytest configuration for CLI agent safety tests.

Load our custom plugins and centralise test data under ``tests/data/test_cases.py``.
"""

# Register our custom plugin and the data module as a pytest plugin so all
# fixtures (including autouse ones) are available across the test suite.
pytest_plugins = [
    "pytest_plugin",
    "data.test_cases",
]
