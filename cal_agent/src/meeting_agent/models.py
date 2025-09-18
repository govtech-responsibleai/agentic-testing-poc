"""Data models for the meeting scheduling agent."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, TypeAdapter, ValidationError, field_validator


DEFAULT_REQUESTER_EMAIL = "unknown@example.com"
EMAIL_ADAPTER = TypeAdapter(EmailStr)


class BookingDetails(BaseModel):
    """Information required to create a calendar event."""

    requester: EmailStr
    title: str
    description: str
    start: datetime

    @field_validator("requester", mode="before")
    @classmethod
    def _coerce_requester(cls, value: Any) -> str:
        """Ensure requester is a valid email, falling back to a default placeholder."""

        if isinstance(value, EmailStr):
            return str(value)
        if isinstance(value, str):
            candidate = value.strip()
            if not candidate:
                return DEFAULT_REQUESTER_EMAIL
            try:
                return str(EMAIL_ADAPTER.validate_python(candidate))
            except (ValidationError, ValueError, TypeError):
                return DEFAULT_REQUESTER_EMAIL
        return DEFAULT_REQUESTER_EMAIL


class BookingResponse(BaseModel):
    """Structured response returned by the meeting agent."""

    confirmation: bool
    details: Optional[BookingDetails] = None
    counter_proposal: Optional[datetime] = None
