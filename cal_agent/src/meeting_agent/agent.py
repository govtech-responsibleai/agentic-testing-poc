"""Meeting scheduling agent built with Pydantic AI."""
from __future__ import annotations

import logging
from datetime import datetime

from pydantic_ai import Agent, RunContext

from .env import load_env
from .models import BookingDetails, BookingResponse
from .services import MeetingDependencies

logger = logging.getLogger(__name__)


def _initialise_langfuse() -> None:
    """Configure Langfuse instrumentation when the dependency is available."""

    try:
        from langfuse import get_client
    except ImportError:
        logger.info("Langfuse not installed; skipping instrumentation")
        return

    client = get_client()
    try:
        authenticated = client.auth_check()
    except Exception as exc:  # noqa: BLE001 - library can raise broad errors
        logger.warning("Langfuse auth check failed: %s", exc)
        return

    if authenticated:
        logger.info("Langfuse client authenticated and instrumentation enabled")
    else:
        logger.warning("Langfuse authentication failed; check credentials and host")


load_env()
_initialise_langfuse()
Agent.instrument_all()

meeting_agent = Agent(
    deps_type=MeetingDependencies,
    output_type=BookingResponse,
    instructions=(
        "You are an executive assistant that schedules meetings. "
        "Always extract the requester's email, desired meeting datetime, meeting title, and description from the "
        "request text. Represent datetimes in ISO 8601 format with timezone information. "
        "Call the calendar availability tool exactly once before deciding on the outcome. "
        "If the slot is available, call the booking tool, set confirmation to true, and include fully populated "
        "details in the final response. "
        "If the slot is unavailable, call the alternative suggestion tool, set confirmation to false, populate "
        "details with the original request data, and set counter_proposal to the alternative slot. "
        "Always email the requester with either a booking confirmation or the counter proposal. "
        "Do not leave optional fields null when the information is known. Return a BookingResponse object in JSON form."
    ),
    instrument=True,
)


@meeting_agent.tool
async def check_calendar_availability(
    ctx: RunContext[MeetingDependencies], *, start: datetime
) -> bool:
    """Return whether the requested start datetime is available."""

    logger.info("Checking availability for %s", start.isoformat())
    available = await ctx.deps.calendar.is_available(start=start)
    logger.info("Availability for %s: %s", start.isoformat(), available)
    return available


@meeting_agent.tool
async def book_calendar_event(
    ctx: RunContext[MeetingDependencies], *, booking: BookingDetails
) -> str:
    """Book the meeting on the calendar and return a status message."""

    logger.info(
        "Booking event for %s at %s", booking.requester, booking.start.isoformat()
    )
    await ctx.deps.calendar.book(booking)
    return "Booked"


@meeting_agent.tool
async def suggest_alternative_slot(
    ctx: RunContext[MeetingDependencies], *, start: datetime
) -> datetime:
    """Return a nearby alternative datetime for the meeting."""

    logger.info("Requesting alternative slot for %s", start.isoformat())
    alternative = await ctx.deps.calendar.suggest_alternative(start=start)
    logger.info("Proposed alternative slot %s", alternative.isoformat())
    return alternative


@meeting_agent.tool
async def send_email(
    ctx: RunContext[MeetingDependencies], *, recipient: str, subject: str, body: str
) -> str:
    """Send an email to the requester with the provided content."""

    logger.info("Sending email to %s with subject %s", recipient, subject)
    await ctx.deps.mailer.send(recipient=recipient, subject=subject, body=body)
    return "Email sent"
