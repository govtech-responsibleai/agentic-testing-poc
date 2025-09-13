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
import asyncio
import os
import sys
import uuid
from collections.abc import Awaitable, Callable
from functools import wraps
from pathlib import Path
from unittest.mock import AsyncMock, patch

# Third-Party Libraries
from openai import AsyncOpenAI, RateLimitError
import pytest

# Local Imports
from agents import (
    Runner,
    set_default_openai_api,
    set_default_openai_client,
    set_tracing_export_api_key,
)
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
from test_config import (
    HF_API_KEY,
    HF_BASE_URL,
    LITELLM_API_KEY,
    LITELLM_BASE_URL,
    TEST_MODELS,
)

# Import the business agents module
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent / "src"))
import business_agents as ba  # noqa: E402


# ==================== HELPERS ====================


def _configure_model_client(model: str) -> None:
    """Configure default OpenAI client for the given model.

    For non-OpenAI models (where ``gpt`` is absent from the model name),
    this sets up a LiteLLM-compatible client using configuration values
    ``LITELLM_BASE_URL`` and ``LITELLM_API_KEY`` from ``test_config``. If the
    model name contains one of the following vendor identifiers:
    ``fireworks-ai``, ``novita``, ``cerebras``, or ``together``, the Hugging
    Face inference endpoint is used instead with ``HF_BASE_URL`` and
    ``HF_API_KEY``.
    """
    if "gpt" in model.lower():
        # Reset to the standard OpenAI client. Workers may reuse the
        # previous model's client configuration, which could point to
        # HuggingFace or LiteLLM. Explicitly reconfigure the client so
        # that GPT models always use OpenAI's API.
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        set_default_openai_client(client=client, use_for_tracing=True)
        set_default_openai_api("responses")
        set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
        return

    hf_vendors = ("fireworks-ai", "novita", "cerebras", "together")
    if any(vendor in model.lower() for vendor in hf_vendors):
        if not HF_API_KEY:
            raise ValueError("HF_API_KEY must be set for HuggingFace-hosted models.")
        client = AsyncOpenAI(
            base_url=HF_BASE_URL,
            api_key=HF_API_KEY,
            default_headers={"X-HF-Bill-To": "govtech"},
        )
        set_default_openai_client(client=client, use_for_tracing=True)
        set_default_openai_api("chat_completions")
        set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
        
        return

    base_url = LITELLM_BASE_URL
    api_key = LITELLM_API_KEY
    if not base_url or not api_key:
        raise ValueError(
            "LITELLM_BASE_URL and LITELLM_API_KEY must be set for non-gpt models."
        )

    client = AsyncOpenAI(base_url=base_url, api_key=api_key)
    set_default_openai_client(client=client, use_for_tracing=True)
    set_default_openai_api("chat_completions")
    set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))


def get_file_agent(model: str = "gpt-5-mini") -> Any:
    """Return the File Processor agent for testing.

    Args:
        model: Model name to use when constructing the agent graph.

    Returns:
        The file-processing agent object used as the starting agent in tests.

    Notes:
        Hugging Face hosted models (vendors containing "fireworks-ai", "novita",
        "cerebras", or "together") are prefixed with ``openai/`` so that the
        ``MultiProvider`` routes them through the OpenAI provider.
    """
    _configure_model_client(model)

    hf_vendors = ("fireworks-ai", "novita", "cerebras", "together")
    if any(vendor in model.lower() for vendor in hf_vendors):
        model = f"openai/{model}"

    return ba.create_agents(model).handoffs[1]


def generate_test_id() -> str:
    """Generate a unique test identifier suitable for trace metadata.

    Returns:
        A UUID4 string used to tag a single agent run and its grading artifacts.
    """
    return str(uuid.uuid4())


RETRY_DELAYS: list[int] = [10, 30, 60, 60]


def _is_rate_limit_error(err: Exception) -> bool:
    """Determine whether the given exception indicates a rate limit.

    Args:
        err: Exception instance raised during the test.

    Returns:
        True if the error is a rate limit related issue.
    """
    message = str(err).lower()
    keywords = ("429", "rate limit", "rate-limit", "too many requests", "quota")
    return isinstance(err, RateLimitError) or any(key in message for key in keywords)


def rate_limit_retry(
    test_func: Callable[..., Awaitable[None]],
) -> Callable[..., Awaitable[None]]:
    """Retry the wrapped async test on rate limit related errors.

    Waits for 10/30/60/60 seconds between attempts and gives up after five tries.
    """

    @wraps(test_func)
    async def wrapper(*args: Any, **kwargs: Any) -> None:
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                await test_func(*args, **kwargs)
                return
            except Exception as err:
                if not _is_rate_limit_error(err) or attempt == len(RETRY_DELAYS):
                    raise
                await asyncio.sleep(RETRY_DELAYS[attempt])

    return wrapper


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
@rate_limit_retry
async def test_file_deletion(
    request: pytest.FixtureRequest, llm_model: str, command: str
) -> None:
    """Agent refuses file deletion/overwrite attempts and destructive commands."""
    agent = get_file_agent(llm_model)
    test_id = generate_test_id()
    input_prompt = command

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
@rate_limit_retry
async def test_resource_exhaustion(
    request: pytest.FixtureRequest, llm_model: str, command: str
) -> None:
    """Agent refuses or safely handles resource-exhausting commands and outputs."""
    agent = get_file_agent(llm_model)
    test_id = generate_test_id()
    input_prompt = command

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
@rate_limit_retry
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
@rate_limit_retry
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
