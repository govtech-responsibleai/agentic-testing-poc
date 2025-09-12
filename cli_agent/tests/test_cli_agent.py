"""
Simplified safety tests for CLI agent responses.

Four risk categories, each covered by a single parametrized test function:
1. File deletion/overwriting attacks
2. Resource exhaustion via file operations
3. PII/sensitive data exposure from files
4. Prompt injection via file contents
"""

from __future__ import annotations

from typing import Any, Tuple

# Standard Libraries
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Third-Party Libraries
import pytest

# Local Imports
from agents import Runner
from agents.run import RunConfig
from graders import (
    handles_sensitive_data_safely,
    refused_user_request,
    resists_prompt_injection,
)
from data.test_cases import (
    FILE_DELETION_COMMANDS,
    RESOURCE_EXHAUSTION_COMMANDS,
    PII_DATA_CASES,
    PROMPT_INJECTION_CASES,
)
from pytest_plugin import capture_test_results
from test_config import TEST_MODELS

# Import the business agents module
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))
import business_agents as ba  # noqa: E402


# ==================== HELPERS ====================


def get_file_agent(model: str = "gpt-5-mini") -> Any:
    """Return the File Processor agent for testing.

    Args:
        model: Model name to use when constructing the agent graph.

    Returns:
        The file-processing agent object used as the starting agent in tests.
    """
    return ba.create_agents(model).handoffs[1]


def generate_test_id() -> str:
    """Generate a unique test identifier suitable for trace metadata.

    Returns:
        A UUID4 string used to tag a single agent run and its grading artifacts.
    """
    return str(uuid.uuid4())


@pytest.fixture
def llm_model(request: pytest.FixtureRequest) -> str:
    """Provide the LLM model name via indirect parametrization.

    Using an explicit fixture avoids decorator-order and plugin interactions
    that can cause pytest to look for a fixture named 'model'.

    Args:
        request: Pytest request object carrying the parameter value.

    Returns:
        The model name supplied by @pytest.mark.parametrize(..., indirect=True).
    """
    value = request.param
    assert isinstance(value, str), "llm_model must be parametrized with str values"
    return value


# ==================== TESTS ====================


@pytest.mark.parametrize("llm_model", TEST_MODELS, indirect=True, ids=lambda m: m)
@pytest.mark.parametrize("command", FILE_DELETION_COMMANDS, ids=lambda s: s)
@pytest.mark.asyncio
async def test_file_deletion(
    request: pytest.FixtureRequest, llm_model: str, command: str
) -> None:
    """Agent refuses file deletion/overwrite attempts and destructive commands."""
    agent = get_file_agent(llm_model)
    test_id = generate_test_id()
    input_prompt = f"Please run: {command}"

    with capture_test_results(
        request,
        test_id,
        "file_deletion",
        llm_model,
        input_prompt,
    ) as capture:
        response = await Runner.run(
            starting_agent=agent,
            input=input_prompt,
            run_config=RunConfig(
                trace_metadata={"test_id": test_id, "test_type": "file_deletion"}
            ),
        )
        text = response.final_output
        capture.set_agent_output(text)
        refused = capture.run_grader(
            refused_user_request, text, input_prompt, test_id
        )
        assert refused.passed


@pytest.mark.parametrize("llm_model", TEST_MODELS, indirect=True, ids=lambda m: m)
@pytest.mark.parametrize("command", RESOURCE_EXHAUSTION_COMMANDS, ids=lambda s: s)
@pytest.mark.asyncio
async def test_resource_exhaustion(
    request: pytest.FixtureRequest, llm_model: str, command: str
) -> None:
    """Agent refuses or safely handles resource-exhausting commands and outputs."""
    agent = get_file_agent(llm_model)
    test_id = generate_test_id()
    input_prompt = f"Please run: {command}"

    with capture_test_results(
        request,
        test_id,
        "resource_exhaustion",
        llm_model,
        input_prompt,
    ) as capture:
        response = await Runner.run(
            starting_agent=agent,
            input=input_prompt,
            run_config=RunConfig(
                trace_metadata={"test_id": test_id, "test_type": "resource_exhaustion"}
            ),
        )
        text = response.final_output
        capture.set_agent_output(text)
        refused = capture.run_grader(
            refused_user_request, text, input_prompt, test_id
        )
        assert refused.passed


@pytest.mark.parametrize("llm_model", TEST_MODELS, indirect=True, ids=lambda m: m)
@pytest.mark.parametrize("pii_content", PII_DATA_CASES, ids=lambda t: t[0])
@pytest.mark.asyncio
async def test_pii_data(
    request: pytest.FixtureRequest,
    llm_model: str,
    pii_content: Tuple[str, str],
) -> None:
    """Agent redacts or warns when tool returns PII/sensitive content.

    Also records grader results so they appear in CSV/JSON reports.
    """
    mocked_query, mocked_tool_output = pii_content

    with patch.object(
        ba.run_command, "on_invoke_tool", new=AsyncMock(return_value=mocked_tool_output)
    ):
        agent = get_file_agent(llm_model)
        test_id = generate_test_id()

        with capture_test_results(
            request,
            test_id,
            "pii_data",
            llm_model,
            mocked_query,
        ) as capture:
            response = await Runner.run(
                starting_agent=agent,
                input=mocked_query,
                run_config=RunConfig(
                    trace_metadata={"test_id": test_id, "test_type": "pii_data"}
                ),
            )
            text = response.final_output
            capture.set_agent_output(text)
            pii_safe = capture.run_grader(
                handles_sensitive_data_safely, text, test_id
            )
            assert pii_safe.passed


@pytest.mark.parametrize("llm_model", TEST_MODELS, indirect=True, ids=lambda m: m)
@pytest.mark.parametrize("content", PROMPT_INJECTION_CASES, ids=lambda t: t[0])
@pytest.mark.asyncio
async def test_prompt_injection(
    request: pytest.FixtureRequest,
    llm_model: str,
    content: Tuple[str, str],
) -> None:
    """Agent resists prompt injection present in returned file contents.

    Also records grader results so they appear in CSV/JSON reports.
    """
    mocked_query, mocked_tool_output = content

    with patch.object(
        ba.run_command, "on_invoke_tool", new=AsyncMock(return_value=mocked_tool_output)
    ):
        agent = get_file_agent(llm_model)
        test_id = generate_test_id()

        with capture_test_results(
            request,
            test_id,
            "prompt_injection",
            llm_model,
            mocked_query,
        ) as capture:
            response = await Runner.run(
                starting_agent=agent,
                input=mocked_query,
                run_config=RunConfig(
                    trace_metadata={"test_id": test_id, "test_type": "prompt_injection"}
                ),
            )
            text = response.final_output
            capture.set_agent_output(text)
            inj_safe = capture.run_grader(
                resists_prompt_injection, text, mocked_tool_output, test_id
            )
            assert inj_safe.passed
