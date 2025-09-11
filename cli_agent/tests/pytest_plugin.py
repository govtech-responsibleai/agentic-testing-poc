"""Pytest plugin for CLI agent safety tests with result collection."""

import time
import pytest
from typing import Dict, Any
from datetime import datetime
from result_collector import add_test_result, generate_all_reports, get_collector
from test_config import TEST_REPETITIONS, GENERATE_REPORTS
from graders import (
    acknowledges_restriction,
    warns_about_danger,
    contains_sensitive_data,
    contains_injection_indicators,
    contains_dangerous_patterns,
)


def pytest_configure(config):
    """Configure pytest with our custom markers."""
    config.addinivalue_line("markers", "repeat: mark test to be repeated")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add repetitions using proper pytest mechanisms."""
    if TEST_REPETITIONS <= 1:
        return
    
    new_items = []
    
    for item in items:
        # For each original test item, create repetitions
        for rep in range(TEST_REPETITIONS):
            if rep == 0:
                # Use original item for first repetition
                original_name = item.name
                item.name = f"{original_name}[rep_{rep+1}]"
                item._rep_number = rep + 1
                item._original_name = original_name
                new_items.append(item)
            else:
                # Create new repetitions by modifying the nodeid
                # This avoids the copy() issue with async coroutines
                try:
                    # Clone the item properly for pytest
                    new_item = item.__class__.from_parent(
                        parent=item.parent,
                        name=f"{item._original_name}[rep_{rep+1}]"
                    )
                    
                    # Copy essential attributes
                    essential_attrs = ['function', 'callspec', 'fixturenames', 'keywords', 'own_markers']
                    for attr in essential_attrs:
                        if hasattr(item, attr):
                            try:
                                setattr(new_item, attr, getattr(item, attr))
                            except (AttributeError, TypeError):
                                pass  # Skip if attribute can't be set
                    
                    new_item._rep_number = rep + 1
                    new_item._original_name = item._original_name
                    new_items.append(new_item)
                    
                except Exception as e:
                    # If we can't create new items properly, fall back to single run
                    print(f"Warning: Could not create repetition {rep+1} for {item.name}: {e}")
                    break
    
    items[:] = new_items


def pytest_runtest_setup(item):
    """Set up for each test run."""
    item._start_time = time.time()


def pytest_runtest_teardown(item, nextitem):
    """Tear down after each test run."""
    if hasattr(item, '_start_time'):
        item._execution_time = time.time() - item._start_time


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Collect test results and create reports."""
    outcome = yield
    report = outcome.get_result()
    
    # Only process test execution phase (not setup/teardown)
    if call.when == "call":
        # Extract test information
        test_id = getattr(item, '_test_id', 'unknown')
        test_type = getattr(item, '_test_type', item.name.split('[')[0])
        model = getattr(item, '_model', 'unknown')
        input_prompt = getattr(item, '_input_prompt', 'unknown')
        agent_output = getattr(item, '_agent_output', '')
        execution_time = getattr(item, '_execution_time', 0)
        
        # Determine if test passed
        passed = report.outcome == 'passed'
        failure_reason = None
        if not passed and report.longrepr:
            failure_reason = str(report.longrepr)
        
        # Collect grader results if available
        grader_results = getattr(item, '_grader_results', {})
        
        # Add result to collector
        add_test_result(
            test_id=test_id,
            test_type=test_type,
            model=model,
            input_prompt=input_prompt,
            agent_output=agent_output,
            passed=passed,
            failure_reason=failure_reason,
            grader_results=grader_results,
            execution_time=execution_time
        )


def pytest_sessionfinish(session, exitstatus):
    """Generate reports at the end of test session."""
    if GENERATE_REPORTS:
        # Only generate reports on the master process (not workers)
        is_worker = hasattr(session.config, 'workerinput')
        
        if not is_worker:
            print("\n" + "="*50)
            print("GENERATING TEST REPORTS")
            print("="*50)
            try:
                paths = generate_all_reports()
                print("✓ Reports generated successfully!")
                for report_type, path in paths.items():
                    print(f"  {report_type.upper()}: {path}")
            except Exception as e:
                print(f"✗ Error generating reports: {e}")
                import traceback
                traceback.print_exc()
            print("="*50)


class TestResultCapture:
    """Context manager to capture test execution details."""
    
    def __init__(self, item, test_id: str, test_type: str, model: str, input_prompt: str):
        self.item = item
        self.test_id = test_id
        self.test_type = test_type
        self.model = model
        self.input_prompt = input_prompt
        self.grader_results = {}
    
    def __enter__(self):
        # Store test metadata on the pytest item
        self.item._test_id = self.test_id
        self.item._test_type = self.test_type
        self.item._model = self.model
        self.item._input_prompt = self.input_prompt
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Store final results
        self.item._grader_results = self.grader_results
    
    def set_agent_output(self, output: str):
        """Set the agent's output response."""
        self.item._agent_output = output
    
    def add_grader_result(self, grader_name: str, result: Any):
        """Add a grader result."""
        self.grader_results[grader_name] = result
    
    def run_grader(self, grader_func, *args, **kwargs):
        """Run a grader function and store the result."""
        try:
            result = grader_func(*args, **kwargs)
            grader_name = grader_func.__name__
            self.add_grader_result(grader_name, result)
            return result
        except Exception as e:
            grader_name = grader_func.__name__
            self.add_grader_result(f"{grader_name}_error", str(e))
            raise


def capture_test_results(request, test_id: str, test_type: str, model: str, input_prompt: str):
    """Factory function to create TestResultCapture instance."""
    return TestResultCapture(request.node, test_id, test_type, model, input_prompt)
