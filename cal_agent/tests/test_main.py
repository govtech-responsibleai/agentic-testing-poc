"""Tests for the CLI entrypoint utilities."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

import main
from meeting_agent.models import BookingDetails, BookingResponse
from meeting_agent.services import SentEmail


class _FakeAgent:
    def __init__(
        self,
        response: BookingResponse,
        *,
        email: SentEmail | None = None,
    ) -> None:
        self._response = response
        self._email = email
        self.received_requests: list[str] = []

    async def run(
        self,
        request: str,
        *,
        deps: Any,  # noqa: ARG002 - used implicitly by interface
        model: str | None = None,
    ) -> SimpleNamespace:
        self.received_requests.append(request)
        if self._email is not None:
            await deps.mailer.send(
                recipient=self._email.recipient,
                subject=self._email.subject,
                body=self._email.body,
            )
        return SimpleNamespace(output=self._response)


@pytest.mark.asyncio
async def test_run_agent_returns_summary_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_run_agent` emits a summary payload and captured emails."""

    booking = BookingDetails(
        requester="alice@example.com",
        title="Sync",
        description="Weekly catch-up",
        start=datetime(2025, 1, 2, 15, tzinfo=timezone.utc),
    )
    response = BookingResponse(
        confirmation=True,
        details=booking,
        counter_proposal=datetime(2025, 1, 2, 16, tzinfo=timezone.utc),
    )
    fake_email = SentEmail(
        recipient="alice@example.com",
        subject="Meeting confirmation",
        body="Your meeting is confirmed.",
    )
    fake_agent = _FakeAgent(response, email=fake_email)
    monkeypatch.setattr(main, "meeting_agent", fake_agent)

    payload, sent_emails = await main._run_agent(
        "alice@example.com", "Schedule a catch-up"
    )

    assert payload == {
        "requester_email": "alice@example.com",
        "request": "Schedule a catch-up",
    }
    assert fake_agent.received_requests == [
        "Schedule a catch-up\nRequester email: alice@example.com"
    ]
    assert sent_emails == [fake_email]


def test_main_interactive_flow(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    """Interactive loop prints responses and writes logs to file."""

    booking = BookingDetails(
        requester="bob@example.com",
        title="Planning",
        description="Discuss roadmap",
        start=datetime(2025, 2, 10, 9, tzinfo=timezone.utc),
    )
    response = BookingResponse(
        confirmation=False,
        details=booking,
        counter_proposal=datetime(2025, 2, 10, 10, tzinfo=timezone.utc),
    )
    fake_email = SentEmail(
        recipient="bob@example.com",
        subject="Proposed alternative",
        body="We could meet at 10:00 UTC instead.",
    )
    fake_agent = _FakeAgent(response, email=fake_email)
    monkeypatch.setattr(main, "meeting_agent", fake_agent)
    monkeypatch.setattr(main, "load_env", lambda: None)
    monkeypatch.setattr(main, "_session_now", lambda: datetime(2025, 2, 10, 9, 30, 15))

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    monkeypatch.setattr(
        main,
        "parse_args",
        lambda: SimpleNamespace(log_file=None, log_dir=str(log_dir)),
    )

    user_inputs: Iterator[str] = iter(["bob@example.com", "Plan meeting", "quit"])
    monkeypatch.setattr("builtins.input", lambda _: next(user_inputs))

    main.main()

    stdout = capsys.readouterr().out
    assert "Meeting scheduler ready" in stdout
    assert "Goodbye!" in stdout
    assert "Email sent:" in stdout
    assert "To: bob@example.com" in stdout
    assert "Subject: Proposed alternative" in stdout
    assert "Body:" in stdout
    assert "We could meet at 10:00 UTC instead." in stdout

    json_start = stdout.index("{")
    json_end = stdout.rindex("}") + 1
    payload = json.loads(stdout[json_start:json_end])
    assert payload == {
        "requester_email": "bob@example.com",
        "request": "Plan meeting",
    }

    session_logs = list(log_dir.iterdir())
    assert session_logs == [log_dir / "2025-02-10-093015_log.log"]

    logged_text = session_logs[0].read_text()
    assert "Processing meeting request" in logged_text

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        handler.close()
        root_logger.removeHandler(handler)


def test_configure_logging_writes_to_file(tmp_path: Path) -> None:
    """`_configure_logging` routes log messages to the specified file."""

    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "agent.log"
    main._configure_logging(str(log_file))
    logging.getLogger("dummy").info("Hello world")
    assert log_file.exists()
    assert "Hello world" in log_file.read_text()

    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        handler.close()
        root_logger.removeHandler(handler)
