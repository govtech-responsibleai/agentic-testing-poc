"""
Simplified safety tests for CLI agent responses.

Four risk categories, each covered by a single parametrized test function:
1. File deletion/overwriting attacks
2. Resource exhaustion via file operations
3. PII/sensitive data exposure from files
4. Prompt injection via file contents
"""

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
from fixtures.test_cases import (
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
import business_agents as ba


# ==================== HELPERS ====================


def get_file_agent(model: str = "gpt-5-mini"):
    """Return the File Processor agent for testing."""
    return ba.create_agents(model).handoffs[1]


def generate_test_id() -> str:
    return str(uuid.uuid4())


# ==================== TESTS ====================


@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
@pytest.mark.parametrize("command", FILE_DELETION_COMMANDS)
async def test_file_deletion(request, model, command):
    """Agent refuses file deletion/overwrite attempts and destructive commands."""

    agent = get_file_agent(model)
    test_id = generate_test_id()
    input_prompt = f"Please run: {command}"

    with capture_test_results(
        request,
        test_id,
        "file_deletion",
        model,
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
        refused = capture.run_grader(refused_user_request, text, test_id)
        assert refused.passed


@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
@pytest.mark.parametrize("command", RESOURCE_EXHAUSTION_COMMANDS)
async def test_resource_exhaustion(request, model, command):
    """Agent refuses or safely handles resource-exhausting commands and outputs."""

    agent = get_file_agent(model)
    test_id = generate_test_id()
    input_prompt = f"Please run: {command}"

    with capture_test_results(
        request,
        test_id,
        "resource_exhaustion",
        model,
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
        refused = capture.run_grader(refused_user_request, text, test_id)
        assert refused.passed


@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
@pytest.mark.parametrize("pii_content", PII_DATA_CASES)
async def test_pii_data(request, model, pii_content):
    """Agent redacts or warns when tool returns PII/sensitive content.

    Also records grader results so they appear in CSV/JSON reports.
    """

    mocked_query = pii_content[0]
    mocked_tool_output = pii_content[1]

    with patch.object(
        ba.run_command, "on_invoke_tool", new=AsyncMock(return_value=mocked_tool_output)
    ):
        agent = get_file_agent(model)
        test_id = generate_test_id()

        with capture_test_results(
            request,
            test_id,
            "pii_data",
            model,
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
            pii_safe = capture.run_grader(handles_sensitive_data_safely, text, test_id)
            assert pii_safe.passed


@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
@pytest.mark.parametrize("content", PROMPT_INJECTION_CASES)
async def test_prompt_injection(request, model, content):
    """Agent resists prompt injection present in returned file contents.

    Also records grader results so they appear in CSV/JSON reports.
    """

    mocked_query = content[0]
    mocked_tool_output = content[1]

    with patch.object(
        ba.run_command, "on_invoke_tool", new=AsyncMock(return_value=mocked_tool_output)
    ):
        agent = get_file_agent(model)
        test_id = generate_test_id()

        with capture_test_results(
            request,
            test_id,
            "prompt_injection",
            model,
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
            inj_safe = capture.run_grader(resists_prompt_injection, text, test_id)
            assert inj_safe.passed
