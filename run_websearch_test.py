#!/usr/bin/env python
"""
Quick runner script to test the websearch agent safety test.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up environment
os.environ["PYTHONPATH"] = str(project_root)

# Run the test
if __name__ == "__main__":
    import pytest
    
    # Run only the websearch test with verbose output
    exit_code = pytest.main([
        "tests/agentic_testing/test_websearch_agent.py::TestWebSearchAgent::test_search_and_check_safety",
        "-v",  # Verbose
        "-s",  # No capture (show print statements)
        "--tb=short"  # Short traceback format
    ])
    
    sys.exit(exit_code)