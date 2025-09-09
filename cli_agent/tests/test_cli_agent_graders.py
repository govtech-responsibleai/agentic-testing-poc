"""Additional safety evaluations for the CLI agent.

These tests reuse fixtures and evaluate responses with graders for
sensitive data exposure and prompt injection attempts.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from agents import Runner

import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))
import business_agents as ba

from fixtures.test_cases import (
    PII_EXPOSURE_TEST_CASES,
    PROMPT_INJECTION_TEST_CASES,
    DANGEROUS_RESPONSE_PATTERNS,
    credentials_file_content,
    prompt_injection_env_leak,
)
from graders import (
    contains_sensitive_data,
    contains_injection_indicators,
    contains_dangerous_patterns,
)


# Helper to create the file agent

def get_file_agent(model: str = "gpt-5-mini"):
    """Return the File Processor agent."""
    return ba.create_agents(model).handoffs[1]


TEST_MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]


@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
@pytest.mark.parametrize("test_case", PII_EXPOSURE_TEST_CASES)
async def test_agent_handles_pii_cases(model, test_case, request):
    """Ensure agent responses do not expose sensitive data."""
    agent = get_file_agent(model)
    content = request.getfixturevalue(test_case["content_fixture"])
    command = test_case["commands"][0]
    with patch.object(ba, "run_command", return_value=content):
        response = await Runner.run(agent, f"Please run: {command}")
        text = response.final_output
        assert not contains_sensitive_data(text, test_case["sensitive_patterns"])


@pytest.mark.asyncio
@pytest.mark.parametrize("model", TEST_MODELS)
@pytest.mark.parametrize("test_case", PROMPT_INJECTION_TEST_CASES)
async def test_agent_resists_prompt_injection_cases(model, test_case, request):
    """Check that prompt injection indicators are absent from responses."""
    agent = get_file_agent(model)
    content = request.getfixturevalue(test_case["content_fixture"])
    command = test_case["commands"][0]
    with patch.object(ba, "run_command", return_value=content):
        response = await Runner.run(agent, f"Please run: {command}")
        text = response.final_output
        assert not contains_injection_indicators(text, test_case["injection_indicators"])
        assert not contains_dangerous_patterns(text, DANGEROUS_RESPONSE_PATTERNS)
