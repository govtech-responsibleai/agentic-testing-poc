"""Pytest plugin for meeting agent safety evaluations."""

from __future__ import annotations

import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from .result_collector import (
    add_test_result,
    generate_all_reports,
    get_collector,
)
from .test_config import GENERATE_REPORTS, REPORTS_DIR, TEST_REPETITIONS

SESSION_ID: str | None = None


def _reports_dir() -> Path:
    directory = Path(REPORTS_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _classify_failure_reason(message: str) -> tuple[bool, bool, bool]:
    lowered = message.lower()
    fail_timeout = any(
        keyword in lowered
        for keyword in (
            "timeout",
            "maxturnsexceeded",
            "usagelimitexceeded",
            "request_limit",
        )
    )
    fail_rate_limit = any(
        keyword in lowered for keyword in ("429", "rate limit", "quota")
    )
    fail_no_cal = "calendar tool was not invoked" in lowered
    return fail_timeout, fail_rate_limit, fail_no_cal


def pytest_configure(config: pytest.Config) -> None:
    """Configure custom markers and establish a session identifier."""

    config.addinivalue_line("markers", "repeat: mark test to be repeated")

    global SESSION_ID
    is_worker = hasattr(config, "workerinput")

    marker_path = _reports_dir() / ".session_id"
    if not is_worker:
        SESSION_ID = (
            datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:8]}"
        )
        try:
            marker_path.write_text(SESSION_ID, encoding="utf-8")
        except Exception:
            pass
    else:
        session_id = None
        for _ in range(50):
            try:
                if marker_path.exists():
                    session_id = marker_path.read_text(encoding="utf-8").strip()
                    break
            except Exception:
                pass
            time.sleep(0.02)
        SESSION_ID = session_id or (
            datetime.now().strftime("%Y%m%d_%H%M%S") + f"_{uuid.uuid4().hex[:8]}"
        )

    try:
        get_collector().set_session_id(SESSION_ID)
    except Exception:
        pass


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Duplicate test items when repetitions are requested and fixtures allow it."""

    if TEST_REPETITIONS <= 1:
        return

    if any("run_iteration" in getattr(item, "fixturenames", ()) for item in items):
        return

    new_items: list[pytest.Item] = []
    for item in items:
        for repetition in range(TEST_REPETITIONS):
            if repetition == 0:
                original_name = item.name
                item.name = f"{original_name}[rep_{repetition + 1}]"
                item._rep_number = repetition + 1  # type: ignore[attr-defined]
                item._original_name = original_name  # type: ignore[attr-defined]
                new_items.append(item)
                continue

            try:
                clone = item.__class__.from_parent(
                    parent=item.parent,
                    name=f"{item._original_name}[rep_{repetition + 1}]",  # type: ignore[attr-defined]
                    callobj=getattr(item, "function", None),
                )
                essential_attrs = [
                    "function",
                    "callspec",
                    "fixturenames",
                    "keywords",
                    "own_markers",
                    "obj",
                ]
                for attribute in essential_attrs:
                    if hasattr(item, attribute):
                        try:
                            setattr(clone, attribute, getattr(item, attribute))
                        except Exception:
                            pass

                clone._rep_number = repetition + 1  # type: ignore[attr-defined]
                clone._original_name = item._original_name  # type: ignore[attr-defined]
                new_items.append(clone)
            except Exception as error:
                print(
                    f"Warning: Could not create repetition {repetition + 1} for {item.name}: {error}"
                )
                break

    items[:] = new_items


def pytest_runtest_setup(item: pytest.Item) -> None:
    item._start_time = time.time()  # type: ignore[attr-defined]


def pytest_runtest_teardown(item: pytest.Item, nextitem: pytest.Item | None) -> None:
    if hasattr(item, "_start_time"):
        item._execution_time = time.time() - item._start_time  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def auto_capture_agent_results(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest):
    """Capture meeting agent inputs and outputs for every test run."""

    try:
        from meeting_agent.agent import meeting_agent
    except Exception:
        yield
        return

    original_run = meeting_agent.run

    async def wrapped_run(*args: Any, **kwargs: Any):
        if args and isinstance(args[0], str):
            request.node._input_prompt = args[0]  # type: ignore[attr-defined]
        if "model" in kwargs and not hasattr(request.node, "_model"):
            request.node._model = kwargs["model"]  # type: ignore[attr-defined]

        response = await original_run(*args, **kwargs)

        output = getattr(response, "output", None)
        if output is None:
            try:
                output_str = str(response)
            except Exception:
                output_str = ""
        else:
            try:
                output_str = output.model_dump_json()
            except Exception:
                try:
                    output_str = str(output)
                except Exception:
                    output_str = ""

        request.node._agent_output = output_str  # type: ignore[attr-defined]
        return response

    monkeypatch.setattr(meeting_agent, "run", wrapped_run, raising=True)
    try:
        yield
    finally:
        try:
            monkeypatch.setattr(meeting_agent, "run", original_run, raising=True)
        except Exception:
            pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo[Any]):
    """Collect structured test results after each call phase."""

    outcome = yield
    report = outcome.get_result()

    if call.when != "call":
        return

    test_id = getattr(item, "_test_id", "unknown")
    test_type = getattr(item, "_test_type", item.name.split("[")[0])
    model = getattr(item, "_model", "unknown")
    input_prompt = getattr(item, "_input_prompt", "unknown")
    agent_output = getattr(item, "_agent_output", "")
    execution_time = getattr(item, "_execution_time", 0.0)
    email_sent_attr = getattr(item, "_email_sent", None)
    email_sent = bool(email_sent_attr)

    if model == "unknown" and hasattr(item, "callspec"):
        params = getattr(item.callspec, "params", {})
        if "llm_model" in params:
            model = params["llm_model"]

    if not test_id or test_id == "unknown":
        base = f"{item.nodeid}:{getattr(item, '_rep_number', 1)}:{datetime.utcnow().isoformat()}"
        test_id = base

    if "run_iteration" in getattr(item, "fixturenames", ()):  # type: ignore[attr-defined]
        try:
            run_num = int(item.callspec.params.get("run_iteration", 1))  # type: ignore[union-attr]
        except Exception:
            run_num = 1
    else:
        run_num = getattr(item, "_rep_number", 1)

    passed = report.outcome == "passed"
    failure_reason = None
    fail_timeout = False
    fail_rate_limit = False
    fail_no_cal = False

    if not passed and report.longrepr:
        failure_reason = str(report.longrepr)
        fail_timeout, fail_rate_limit, fail_no_cal = _classify_failure_reason(
            failure_reason
        )

    try:
        graders = getattr(item, "_grader_results", {})
    except Exception:
        graders = {}

    add_test_result(
        test_id=test_id,
        test_type=test_type,
        run_num=run_num,
        model=model,
        input_prompt=input_prompt,
        agent_output=agent_output,
        passed=passed,
        failure_reason=failure_reason,
        grader_results=graders,
        execution_time=execution_time,
        fail_timeout=fail_timeout,
        fail_rate_limit=fail_rate_limit,
        email_sent=email_sent,
        fail_no_cal=fail_no_cal,
    )


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Generate end-of-session reports when enabled."""

    if not GENERATE_REPORTS:
        return

    if hasattr(session.config, "workerinput"):
        return

    print("\n" + "=" * 50)
    print("GENERATING MEETING AGENT TEST REPORTS")
    print("=" * 50)
    try:
        paths = generate_all_reports()
        if paths:
            print("✓ Reports generated successfully!")
            for name, path in paths.items():
                print(f"  {name.upper()}: {path}")
    except Exception as error:
        print(f"✗ Error generating reports: {error}")
        import traceback

        traceback.print_exc()
    print("=" * 50)


class TestResultCapture:
    """Context manager used within tests to record metadata and grader output."""

    def __init__(
        self,
        item: pytest.Item,
        *,
        test_id: str,
        test_type: str,
        model: str,
        input_prompt: str,
        run_num: int | None = None,
    ) -> None:
        self.item = item
        self.test_id = test_id
        self.test_type = test_type
        self.model = model
        self.input_prompt = input_prompt
        self.run_num = run_num
        self.grader_results: dict[str, Any] = {}
        self.email_sent: bool | None = None

    def __enter__(self) -> "TestResultCapture":
        self.item._test_id = self.test_id  # type: ignore[attr-defined]
        self.item._test_type = self.test_type  # type: ignore[attr-defined]
        self.item._model = self.model  # type: ignore[attr-defined]
        self.item._input_prompt = self.input_prompt  # type: ignore[attr-defined]
        if self.run_num is not None:
            self.item._rep_number = self.run_num  # type: ignore[attr-defined]
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[override]
        self.item._grader_results = self.grader_results  # type: ignore[attr-defined]
        if self.email_sent is not None:
            self.item._email_sent = self.email_sent  # type: ignore[attr-defined]

    def set_agent_output(self, output: str) -> None:
        """Attach the agent's final output for reporting."""

        self.item._agent_output = output  # type: ignore[attr-defined]

    def add_grader_result(self, grader_name: str, result: Any) -> None:
        """Store a grader response, supporting Pydantic models transparently."""

        try:
            from pydantic import BaseModel

            if isinstance(result, BaseModel):
                self.grader_results[grader_name] = result.model_dump()
                return
        except Exception:
            pass

        self.grader_results[grader_name] = result

    def set_email_sent(self, sent: bool) -> None:
        """Record whether the agent produced at least one outbound email."""

        self.email_sent = sent
        self.item._email_sent = sent  # type: ignore[attr-defined]


def capture_test_results(
    request: pytest.FixtureRequest,
    *,
    test_id: str,
    test_type: str,
    model: str,
    input_prompt: str,
    run_num: int | None = None,
) -> TestResultCapture:
    """Factory that aligns the context manager signature with test usage."""

    return TestResultCapture(
        request.node,
        test_id=test_id,
        test_type=test_type,
        model=model,
        input_prompt=input_prompt,
        run_num=run_num,
    )
