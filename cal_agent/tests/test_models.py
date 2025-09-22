"""Tests for model coercion and defaults."""
from __future__ import annotations

from datetime import datetime, timezone

from meeting_agent.models import BookingDetails, DEFAULT_REQUESTER_EMAIL


def test_booking_details_invalid_email_falls_back_to_placeholder() -> None:
    """Invalid requester emails are coerced to the default placeholder."""

    details = BookingDetails(
        requester="unknown@unknown",
        title="Coffee",
        description="Catch up",
        start=datetime(2025, 5, 5, 12, tzinfo=timezone.utc),
    )

    assert details.requester == DEFAULT_REQUESTER_EMAIL


def test_booking_details_blank_email_falls_back_to_placeholder() -> None:
    """Blank requester emails are coerced to the default placeholder."""

    details = BookingDetails(
        requester="  ",
        title="Standup",
        description="Daily sync",
        start=datetime(2025, 5, 6, 9, tzinfo=timezone.utc),
    )

    assert details.requester == DEFAULT_REQUESTER_EMAIL
