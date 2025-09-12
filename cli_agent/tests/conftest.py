"""Pytest configuration for CLI agent safety tests.

Load our custom plugins and centralise fixtures under ``tests/fixtures/test_cases.py``.
"""

# Register our custom plugin and the fixtures module as a pytest plugin so all
# fixtures (including autouse ones) are available across the test suite.
pytest_plugins = [
    "pytest_plugin",
    "fixtures.test_cases",
]
