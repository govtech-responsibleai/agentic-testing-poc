"""Support services and dependencies used by the meeting agent."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from random import Random
from typing import Optional

from .models import BookingDetails


class MockCalendarService:
    """Mocked Google Calendar integration using a pseudo-random availability check."""

    def __init__(self, *, rng: Optional[Random] = None) -> None:
        self._rng = rng or Random()
        self._booked_events: list[BookingDetails] = []

    async def is_available(self, start: datetime) -> bool:
        """Return a pseudo-random availability flag for the requested slot."""

        return self._rng.choice([True, False])

    async def book(self, booking: BookingDetails) -> None:
        """Store the booked event details for later inspection."""

        self._booked_events.append(booking)

    async def suggest_alternative(self, start: datetime) -> datetime:
        """Provide a deterministic counter proposal one hour later."""

        return start + timedelta(hours=1)

    @property
    def booked_events(self) -> list[BookingDetails]:
        """Expose booked events for testing and debugging."""

        return list(self._booked_events)


@dataclass
class SentEmail:
    """Representation of an email message sent by the mock mailer."""

    recipient: str
    subject: str
    body: str


class MockMailer:
    """Mocked email delivery service capturing outbound messages."""

    def __init__(self) -> None:
        self._outbox: list[SentEmail] = []

    async def send(self, *, recipient: str, subject: str, body: str) -> None:
        """Store the outbound email message."""

        self._outbox.append(SentEmail(recipient=recipient, subject=subject, body=body))

    @property
    def outbox(self) -> list[SentEmail]:
        """Return a copy of captured email messages."""

        return list(self._outbox)


@dataclass
class MeetingDependencies:
    """Container for dependencies shared with the meeting agent."""

    calendar: MockCalendarService = field(default_factory=MockCalendarService)
    mailer: MockMailer = field(default_factory=MockMailer)
