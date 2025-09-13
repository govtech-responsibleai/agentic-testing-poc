"""Pytest plugin for CLI agent safety tests with result collection.

Adds session-scoped worker result files so reports only merge data from the
current test session (prevents cross-run merges from leftover worker files).
"""

import time
import pytest
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import os
from result_collector import add_test_result, generate_all_reports, get_collector
import uuid
from pydantic import BaseModel
from test_config import TEST_REPETITIONS, GENERATE_REPORTS, REPORTS_DIR

# Optional imports for error-type detection; fallback to string checks if unavailable
try:
    from agents.exceptions import MaxTurnsExceeded as _MaxTurnsExceeded
except Exception:  # pragma: no cover - robust in environments without agents pkg
    _MaxTurnsExceeded = None

try:
    from openai import RateLimitError as _RateLimitError
except Exception:  # pragma: no cover - robust in environments without openai pkg
    _RateLimitError = None

# Note: Older pattern-based graders have been removed in favor of
# LLM-based graders invoked directly within specific tests.


SESSION_ID: str | None = None


def _reports_dir() -> Path:
    p = Path(REPORTS_DIR)
    p.mkdir(exist_ok=True)
    return p


def pytest_configure(config):
    """Configure pytest with our custom markers and establish a session id."""
    config.addinivalue_line("markers", "repeat: mark test to be repeated")

    global SESSION_ID
    # Determine if running under xdist worker
    is_worker = hasattr(config, "workerinput")

    marker_path = _reports_dir() / ".session_id"
    if not is_worker:
        # Master process: create a fresh session id and write marker
        SESSION_ID = (
            datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:8]}"
        )
        try:
            marker_path.write_text(SESSION_ID, encoding="utf-8")
        except Exception:
            pass
    else:
        # Worker process: read the session id written by the master
        sid = None
        for _ in range(50):  # wait up to ~1s
            try:
                if marker_path.exists():
                    sid = marker_path.read_text(encoding="utf-8").strip()
                    break
            except Exception:
                pass
            time.sleep(0.02)
        SESSION_ID = sid or (
            datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:8]}"
        )

    # Inform the result collector so it will only merge this session's files
    try:
        get_collector().set_session_id(SESSION_ID)
    except Exception:
        pass


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
                    # Many pytest versions require providing the callable via `callobj`
                    new_item = item.__class__.from_parent(
                        parent=item.parent,
                        name=f"{item._original_name}[rep_{rep+1}]",
                        callobj=getattr(item, "function", None),
                    )

                    # Copy essential attributes where possible so parametrization is preserved
                    essential_attrs = [
                        "function",
                        "callspec",
                        "fixturenames",
                        "keywords",
                        "own_markers",
                        "obj",
                    ]
                    for attr in essential_attrs:
                        if hasattr(item, attr):
                            try:
                                setattr(new_item, attr, getattr(item, attr))
                            except Exception:
                                pass  # Skip if attribute can't be set

                    new_item._rep_number = rep + 1
                    new_item._original_name = item._original_name
                    new_items.append(new_item)

                except Exception as e:
                    # If we can't create new items properly, fall back to single run
                    print(
                        f"Warning: Could not create repetition {rep+1} for {item.name}: {e}"
                    )
                    break

    items[:] = new_items


def pytest_runtest_setup(item):
    """Set up for each test run."""
    item._start_time = time.time()


def pytest_runtest_teardown(item, nextitem):
    """Tear down after each test run."""
    if hasattr(item, "_start_time"):
        item._execution_time = time.time() - item._start_time


@pytest.fixture(autouse=True)
def auto_capture_agent_results(monkeypatch, request):
    """Automatically capture key metadata and agent output for every test.

    This fixture wraps `agents.Runner.run` so we can:
    - Record the `input` prompt passed to the runner
    - Extract `test_id` and `test_type` from `RunConfig.trace_metadata`
    - Capture `response.final_output` as the agent output

    It also pre-fills the `model` from parametrization when available.

    This ensures we capture data even for tests that don't use the
    `capture_test_results` context manager, including failing tests.
    """
    # Pre-fill model from parametrization if present
    try:
        if not hasattr(request.node, "_model"):
            callspec = getattr(request.node, "callspec", None)
            if callspec and "model" in getattr(callspec, "params", {}):
                request.node._model = callspec.params["model"]
    except Exception:
        pass  # Best-effort only

    # Attempt to import the Agents SDK Runner
    try:
        from agents import Runner as AgentsRunner  # type: ignore
    except Exception:
        AgentsRunner = None  # Fallback if not available

    if not AgentsRunner or not hasattr(AgentsRunner, "run"):
        # Nothing to wrap; continue test execution
        yield
        return

    original_run = AgentsRunner.run

    async def wrapped_run(*args, **kwargs):
        # Capture input prompt if provided
        input_prompt = kwargs.get("input")
        if input_prompt and not getattr(request.node, "_input_prompt", None):
            request.node._input_prompt = input_prompt

        # Extract trace metadata from RunConfig if present
        run_config = kwargs.get("run_config")
        trace_metadata = getattr(run_config, "trace_metadata", None)
        if isinstance(trace_metadata, dict):
            # Only set if not already populated by an explicit capture context
            if not getattr(request.node, "_test_id", None):
                tid = trace_metadata.get("test_id")
                if tid:
                    request.node._test_id = tid
            if not getattr(request.node, "_test_type", None):
                ttype = trace_metadata.get("test_type")
                if ttype:
                    request.node._test_type = ttype

        # Execute the original runner and capture output
        response = await original_run(*args, **kwargs)

        # Persist agent output when available
        output = getattr(response, "final_output", None)
        if output is None:
            try:
                output = str(response)
            except Exception:
                output = ""
        request.node._agent_output = output

        return response

    # Patch Runner.run for the duration of the test
    monkeypatch.setattr(AgentsRunner, "run", wrapped_run, raising=True)

    try:
        yield
    finally:
        # Best-effort restore (pytest/monkeypatch also auto-restores)
        try:
            monkeypatch.setattr(AgentsRunner, "run", original_run, raising=True)
        except Exception:
            pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Collect test results and create reports."""
    outcome = yield
    report = outcome.get_result()

    # Only process test execution phase (not setup/teardown)
    if call.when == "call":
        # Extract test information
        test_id = getattr(item, "_test_id", "unknown")
        test_type = getattr(item, "_test_type", item.name.split("[")[0])
        model = getattr(item, "_model", "unknown")
        input_prompt = getattr(item, "_input_prompt", "unknown")
        agent_output = getattr(item, "_agent_output", "")
        execution_time = getattr(item, "_execution_time", 0)

        # Fallbacks for missing metadata
        try:
            # Prefer parametrized model if not explicitly set
            if (
                model == "unknown"
                and hasattr(item, "callspec")
                and "model" in getattr(item.callspec, "params", {})
            ):
                model = item.callspec.params["model"]
        except Exception:
            pass

        # Ensure we always have a unique test_id for traceability
        if not test_id or test_id == "unknown":
            try:
                # Derive a deterministic-ish id from nodeid and time
                base = f"{item.nodeid}:{getattr(item, '_rep_number', 1)}:{datetime.utcnow().isoformat()}"
            except Exception:
                base = str(uuid.uuid4())
            test_id = base

        # Determine if test passed
        passed = report.outcome == "passed"
        failure_reason = None
        fail_timeout = False
        fail_rate_limit = False
        if not passed and report.longrepr:
            failure_reason = str(report.longrepr)
            # Detect MaxTurnsExceeded via string when available
            if "MaxTurnsExceeded" in failure_reason or "Max turns (" in failure_reason:
                fail_timeout = True
            msg = failure_reason.lower()
            if any(
                key in msg
                for key in [
                    "429",
                    "rate limit",
                    "rate-limit",
                    "too many requests",
                    "quota",
                ]
            ):
                fail_rate_limit = True

        # Prefer exception type when available
        try:
            if not passed and getattr(call, "excinfo", None) is not None:
                exc_type = call.excinfo.type
                if _MaxTurnsExceeded is not None and issubclass(
                    exc_type, _MaxTurnsExceeded
                ):
                    fail_timeout = True
                if _RateLimitError is not None and issubclass(
                    exc_type, _RateLimitError
                ):
                    fail_rate_limit = True
        except Exception:
            pass

        # Collect grader results if available
        grader_results = getattr(item, "_grader_results", {})

        # Determine repetition/run number (1-based)
        run_num = getattr(item, "_rep_number", 1)

        # Add result to collector (include run number)
        add_test_result(
            test_id=test_id,
            test_type=test_type,
            run_num=run_num,
            model=model,
            input_prompt=input_prompt,
            agent_output=agent_output,
            passed=passed,
            failure_reason=failure_reason,
            grader_results=grader_results,
            execution_time=execution_time,
            fail_timeout=fail_timeout,
            fail_rate_limit=fail_rate_limit,
        )


def pytest_sessionfinish(session, exitstatus):
    """Generate reports at the end of test session."""
    if GENERATE_REPORTS:
        # Only generate reports on the master process (not workers)
        is_worker = hasattr(session.config, "workerinput")

        if not is_worker:
            print("\n" + "=" * 50)
            print("GENERATING TEST REPORTS")
            print("=" * 50)
            try:
                paths = generate_all_reports()
                print("✓ Reports generated successfully!")
                for report_type, path in paths.items():
                    print(f"  {report_type.upper()}: {path}")
            except Exception as e:
                print(f"✗ Error generating reports: {e}")
                import traceback

                traceback.print_exc()
            print("=" * 50)


class TestResultCapture:
    """Context manager to capture test execution details."""

    def __init__(
        self, item, test_id: str, test_type: str, model: str, input_prompt: str
    ):
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
        """Add a grader result.

        Store grader outputs under a single `grader_results` mapping keyed by
        grader name. If a Pydantic model is provided, persist its dict payload
        without flattening to `.passed`/`.summary` columns so multiple graders
        can coexist cleanly in reports.
        """
        if isinstance(result, BaseModel):
            self.grader_results[grader_name] = result.model_dump()
        else:
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


def capture_test_results(
    request, test_id: str, test_type: str, model: str, input_prompt: str
):
    """Factory function to create TestResultCapture instance."""
    return TestResultCapture(request.node, test_id, test_type, model, input_prompt)
