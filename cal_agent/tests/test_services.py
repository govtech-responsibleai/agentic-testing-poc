"""Unit tests for mocked calendar and mailer services."""
from __future__ import annotations

from datetime import datetime, timezone
from random import Random

import pytest

from meeting_agent.models import BookingDetails
from meeting_agent.services import MeetingDependencies, MockCalendarService, MockMailer


@pytest.mark.asyncio
async def test_calendar_availability_is_seeded() -> None:
    """Seeded RNG yields deterministic availability responses."""

    service = MockCalendarService(rng=Random(1))
    start = datetime(2025, 9, 18, 15, tzinfo=timezone.utc)
    first = await service.is_available(start)
    second = await service.is_available(start)
    assert first is True
    assert second is True


@pytest.mark.asyncio
async def test_calendar_booking_and_alternative() -> None:
    """Booking stores details and alternatives are one hour later."""

    service = MockCalendarService(rng=Random(2))
    booking = BookingDetails(
        requester="requester@example.com",
        title="Project Sync",
        description="Discuss roadmap",
        start=datetime(2025, 9, 18, 10, tzinfo=timezone.utc),
    )
    await service.book(booking)
    assert service.booked_events == [booking]

    alternative = await service.suggest_alternative(booking.start)
    assert alternative == booking.start.replace(hour=11)


@pytest.mark.asyncio
async def test_mailer_records_outbound_messages() -> None:
    """Mailer captures sent emails for inspection."""

    mailer = MockMailer()
    await mailer.send(recipient="recipient@example.com", subject="Hello", body="Body")
    assert len(mailer.outbox) == 1
    message = mailer.outbox[0]
    assert message.recipient == "recipient@example.com"
    assert message.subject == "Hello"
    assert message.body == "Body"


def test_dependencies_provide_defaults() -> None:
    """Dependencies create default service instances."""

    deps = MeetingDependencies()
    assert isinstance(deps.calendar, MockCalendarService)
    assert isinstance(deps.mailer, MockMailer)
