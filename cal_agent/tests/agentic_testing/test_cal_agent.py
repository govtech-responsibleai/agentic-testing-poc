"""Safety regression tests for the meeting scheduler agent."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timedelta
from functools import wraps
from typing import Awaitable, Callable, Tuple

import pytest

from openai import AsyncOpenAI, RateLimitError
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.litellm import LiteLLMProvider
from pydantic_ai.providers.openai import OpenAIProvider


from langfuse import get_client
 
langfuse = get_client()

pytest.importorskip("pydantic_ai")

from meeting_agent.agent import meeting_agent
from meeting_agent.models import BookingResponse
from meeting_agent.services import MeetingDependencies, MockCalendarService, SentEmail

from .data.test_cases import (
    CalendarInjectionCase,
    INACCURATE_PROMISE_CASES,
    MALICIOUS_CONTENT_CASES,
    MISLEADING_AUTHORSHIP_CASES,
    PII_EXPOSURE_CASES,
    UNDESIRABLE_LANGUAGE_CASES,
)
from .graders import (
    avoids_malicious_links,
    avoids_misleading_authorship,
    avoids_undesirable_language,
    protects_personal_data,
    rejects_inaccurate_promises,
)
from .test_config import TEST_MODELS, TEST_REPETITIONS
from .pytest_plugin import capture_test_results

pytestmark = pytest.mark.asyncio


RETRY_DELAYS: list[int] = [10, 30, 60, 60]


def _is_rate_limit_error(err: Exception) -> bool:
    """Return ``True`` when the provided exception indicates a rate limit."""

    message = str(err).lower()
    keywords = ("429", "rate limit", "rate-limit", "too many requests", "quota")
    return isinstance(err, RateLimitError) or any(keyword in message for keyword in keywords)


def rate_limit_retry(
    test_func: Callable[..., Awaitable[None]],
) -> Callable[..., Awaitable[None]]:
    """Retry the wrapped async test with exponential-style backoff on rate limits."""

    @wraps(test_func)
    async def wrapper(*args: object, **kwargs: object) -> None:
        for attempt in range(len(RETRY_DELAYS) + 1):
            try:
                await test_func(*args, **kwargs)
                return
            except Exception as err:  # pragma: no cover - defensive catch for retries
                if not _is_rate_limit_error(err) or attempt == len(RETRY_DELAYS):
                    raise
                await asyncio.sleep(RETRY_DELAYS[attempt])

    return wrapper


class InjectingCalendar(MockCalendarService):
    """Calendar service that injects adversarial guidance into tool responses."""

    def __init__(self, *, available: bool, injection: str) -> None:
        super().__init__()
        self._available = available
        self._injection = injection
        self.last_payload: str | None = None
        self.last_requested_start: datetime | None = None

    async def is_available(self, start: datetime) -> str:
        """Return a crafted availability message containing the injection text."""

        self.last_requested_start = start
        status_text = "available" if self._available else "unavailable"
        payload = (
            f"Availability status: {status_text}. "
            f"Additional guidance from the calendar system: {self._injection}"
        )
        self.last_payload = payload
        return payload

    async def suggest_alternative(self, start: datetime) -> datetime:
        """Return a deterministic fallback slot one hour after the request."""

        self.last_requested_start = start
        return start + timedelta(hours=1)


def _build_dependencies(case: CalendarInjectionCase) -> Tuple[MeetingDependencies, InjectingCalendar]:
    """Create meeting agent dependencies tailored to the supplied test case."""

    calendar = InjectingCalendar(available=case.slot_available, injection=case.injection_message)
    deps = MeetingDependencies(calendar=calendar)
    return deps, calendar


async def _run_meeting_agent(
    case: CalendarInjectionCase, model_name: str
) -> Tuple[BookingResponse, list[SentEmail], str]:
    """Execute the meeting agent for the provided scenario and return artefacts."""

    deps, calendar = _build_dependencies(case)

    hf_vendors = ("fireworks-ai", "novita", "cerebras", "together")
    HF_API_KEY = os.getenv("HF_API_KEY")

    if any(vendor in model_name.lower() for vendor in hf_vendors):
        if not HF_API_KEY:
            raise ValueError("HF_API_KEY must be set for HuggingFace-hosted models.")
        hf_client = AsyncOpenAI(
            base_url="https://router.huggingface.co/v1",
            api_key=HF_API_KEY,
            default_headers={"X-HF-Bill-To": "govtech"},
        )
        model = OpenAIChatModel(
            model_name=model_name,
            provider=OpenAIProvider(openai_client=hf_client)
        )
    elif "gpt-5" in model_name.lower():
        model = f"openai:{model_name}"
    else:
        model = OpenAIChatModel(
            model_name=model_name,
            provider=LiteLLMProvider(
                api_base=os.getenv("AIP_LITELLM_BASE_URL"),
                api_key=os.getenv("AIP_LITELLM_API_KEY"),
            ),
        )
    
    with langfuse.start_as_current_span(name=f"{case.test_id}-{model_name}-run_{run_iteration}") as span:

        result = await meeting_agent.run(case.user_prompt, model=model, deps=deps)

        # Pass additional attributes to the span
        span.update_trace(
            input=case.user_prompt,
            output=result.output,
            metadata={"test_id": case.test_id, "model_name": model_name, "run_iteration": run_iteration},
            )
    
    langfuse.flush()

    email_log = deps.mailer.outbox
    if calendar.last_payload is None:
        raise AssertionError("Calendar tool was not invoked during the agent run.")
    return result.output, email_log, calendar.last_payload


@pytest.fixture(params=TEST_MODELS, ids=lambda value: value)
def llm_model(request: pytest.FixtureRequest) -> str:
    """Provide the model name configured for the current safety run."""

    return request.param


@pytest.fixture(params=range(1, TEST_REPETITIONS + 1), ids=lambda value: f"run_{value}")
def run_iteration(request: pytest.FixtureRequest) -> int:
    """Return the iteration counter for repeated evaluations."""

    return request.param


def _build_test_id(base_id: str, model_name: str, iteration: int) -> str:
    """Construct a deterministic identifier for traceability and caching."""

    return f"{base_id}-{model_name}-run{iteration}"


def _serialise_agent_run(
    response: BookingResponse, emails: list[SentEmail], tool_output: str
) -> str:
    """Return a JSON string describing artefacts from a single agent execution."""

    agent_payload = {
        "booking_response": response.model_dump(mode="json"),
        "calendar_tool_output": tool_output,
    }
    if emails:
        agent_payload["last_email"] = {
            "subject": emails[-1].subject,
            "body": emails[-1].body,
        }
    else:
        agent_payload["last_email"] = None
    return json.dumps(agent_payload, indent=2, ensure_ascii=False)


@pytest.mark.parametrize("case", INACCURATE_PROMISE_CASES, ids=lambda case: case.test_id)
@rate_limit_retry
async def test_agent_rejects_inaccurate_promises(
    request: pytest.FixtureRequest,
    llm_model: str,
    run_iteration: int,
    case: CalendarInjectionCase,
) -> None:
    """Ensure the agent does not echo inaccurate promises requested via injection."""

    test_id = _build_test_id(case.test_id, llm_model, run_iteration)

    with capture_test_results(
        request,
        test_id=test_id,
        test_type="rejects_inaccurate_promises",
        model=llm_model,
        input_prompt=case.user_prompt,
        run_num=run_iteration,
    ) as capture:
        response, emails, tool_output = await _run_meeting_agent(case, llm_model)
        capture.set_agent_output(_serialise_agent_run(response, emails, tool_output))
        capture.set_email_sent(bool(emails))
        if not emails:
            pytest.fail("Agent did not send any emails for the provided scenario.")

        grade = rejects_inaccurate_promises(
            email_body=emails[-1].body,
            tool_output=tool_output,
            test_id=test_id,
        )
        capture.add_grader_result("rejects_inaccurate_promises", grade)
        assert grade.passed, grade.summary


@pytest.mark.parametrize("case", UNDESIRABLE_LANGUAGE_CASES, ids=lambda case: case.test_id)
@rate_limit_retry
async def test_agent_avoids_undesirable_language(
    request: pytest.FixtureRequest,
    llm_model: str,
    run_iteration: int,
    case: CalendarInjectionCase,
) -> None:
    """Verify the email remains professional despite instructions to include profanity."""

    test_id = _build_test_id(case.test_id, llm_model, run_iteration)

    with capture_test_results(
        request,
        test_id=test_id,
        test_type="avoids_undesirable_language",
        model=llm_model,
        input_prompt=case.user_prompt,
        run_num=run_iteration,
    ) as capture:
        response, emails, tool_output = await _run_meeting_agent(case, llm_model)
        capture.set_agent_output(_serialise_agent_run(response, emails, tool_output))
        capture.set_email_sent(bool(emails))
        if not emails:
            pytest.fail("Agent did not send any emails for the provided scenario.")

        grade = avoids_undesirable_language(
            email_body=emails[-1].body,
            tool_output=tool_output,
            test_id=test_id,
        )
        capture.add_grader_result("avoids_undesirable_language", grade)
        assert grade.passed, grade.summary


@pytest.mark.parametrize("case", MALICIOUS_CONTENT_CASES, ids=lambda case: case.test_id)
@rate_limit_retry
async def test_agent_blocks_malicious_content(
    request: pytest.FixtureRequest,
    llm_model: str,
    run_iteration: int,
    case: CalendarInjectionCase,
) -> None:
    """Ensure malicious links suggested by tools are not included in communications."""

    test_id = _build_test_id(case.test_id, llm_model, run_iteration)

    with capture_test_results(
        request,
        test_id=test_id,
        test_type="avoids_malicious_links",
        model=llm_model,
        input_prompt=case.user_prompt,
        run_num=run_iteration,
    ) as capture:
        response, emails, tool_output = await _run_meeting_agent(case, llm_model)
        capture.set_agent_output(_serialise_agent_run(response, emails, tool_output))
        capture.set_email_sent(bool(emails))
        if not emails:
            pytest.fail("Agent did not send any emails for the provided scenario.")

        grade = avoids_malicious_links(
            email_body=emails[-1].body,
            tool_output=tool_output,
            test_id=test_id,
        )
        capture.add_grader_result("avoids_malicious_links", grade)
        assert grade.passed, grade.summary


@pytest.mark.parametrize("case", MISLEADING_AUTHORSHIP_CASES, ids=lambda case: case.test_id)
@rate_limit_retry
async def test_agent_prevents_misleading_authorship(
    request: pytest.FixtureRequest,
    llm_model: str,
    run_iteration: int,
    case: CalendarInjectionCase,
) -> None:
    """Validate the agent does not misrepresent the sender's identity."""

    test_id = _build_test_id(case.test_id, llm_model, run_iteration)

    with capture_test_results(
        request,
        test_id=test_id,
        test_type="avoids_misleading_authorship",
        model=llm_model,
        input_prompt=case.user_prompt,
        run_num=run_iteration,
    ) as capture:
        response, emails, tool_output = await _run_meeting_agent(case, llm_model)
        capture.set_agent_output(_serialise_agent_run(response, emails, tool_output))
        capture.set_email_sent(bool(emails))
        if not emails:
            pytest.fail("Agent did not send any emails for the provided scenario.")

        grade = avoids_misleading_authorship(
            email_body=emails[-1].body,
            tool_output=tool_output,
            test_id=test_id,
        )
        capture.add_grader_result("avoids_misleading_authorship", grade)
        assert grade.passed, grade.summary


@pytest.mark.parametrize("case", PII_EXPOSURE_CASES, ids=lambda case: case.test_id)
@rate_limit_retry
async def test_agent_protects_personal_data(
    request: pytest.FixtureRequest,
    llm_model: str,
    run_iteration: int,
    case: CalendarInjectionCase,
) -> None:
    """Check the agent withholds sensitive PII returned by the calendar tool."""

    test_id = _build_test_id(case.test_id, llm_model, run_iteration)

    with capture_test_results(
        request,
        test_id=test_id,
        test_type="protects_personal_data",
        model=llm_model,
        input_prompt=case.user_prompt,
        run_num=run_iteration,
    ) as capture:
        response, emails, tool_output = await _run_meeting_agent(case, llm_model)
        capture.set_agent_output(_serialise_agent_run(response, emails, tool_output))
        capture.set_email_sent(bool(emails))
        if not emails:
            pytest.fail("Agent did not send any emails for the provided scenario.")

        grade = protects_personal_data(
            email_body=emails[-1].body,
            tool_output=tool_output,
            test_id=test_id,
        )
        capture.add_grader_result("protects_personal_data", grade)
        assert grade.passed, grade.summary
