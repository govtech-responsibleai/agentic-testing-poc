"""CLI entrypoint for the meeting scheduling agent."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from pydantic import ValidationError

from meeting_agent.agent import meeting_agent
from meeting_agent.env import load_env
from meeting_agent.models import DEFAULT_REQUESTER_EMAIL, EMAIL_ADAPTER
from meeting_agent.services import MeetingDependencies, SentEmail

logger = logging.getLogger(__name__)


MODEL = "openai:gpt-5-mini-2025-08-07"

def parse_args() -> argparse.Namespace:
    """Return parsed CLI arguments."""

    parser = argparse.ArgumentParser(description="Interactive meeting scheduling agent")
    parser.add_argument(
        "--log-dir",
        default="log",
        help="Directory where session logs will be stored (default: log)",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional explicit path to the log file; overrides --log-dir when provided.",
    )
    return parser.parse_args()


def _configure_logging(log_file: str | Path) -> None:
    """Configure logging so all records are written to a file."""

    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # Remove existing handlers to avoid duplicate writes when rerunning tests.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def _session_now() -> datetime:
    """Return the current timestamp for session log naming."""

    return datetime.now()


def _session_log_path(log_dir: Path) -> Path:
    """Construct a per-session log path using a timestamp-based filename."""

    timestamp = _session_now().strftime("%Y-%m-%d-%H%M%S")
    return log_dir / f"{timestamp}_log.log"


def _normalise_email(raw_email: str) -> str:
    """Return a validated email or the default placeholder when invalid."""

    candidate = raw_email.strip()
    if not candidate:
        return DEFAULT_REQUESTER_EMAIL
    try:
        return str(EMAIL_ADAPTER.validate_python(candidate))
    except (ValidationError, ValueError, TypeError):
        return DEFAULT_REQUESTER_EMAIL


async def _run_agent(requester_email: str, request: str) -> tuple[dict[str, str], list[SentEmail]]:
    """Execute the agent and return a summary payload plus sent emails."""

    deps = MeetingDependencies()
    email = _normalise_email(requester_email)
    combined_request = f"{request}\nRequester email: {email}"
    logger.info("Processing meeting request")
    result = await meeting_agent.run(combined_request, model=MODEL, deps=deps)
    output = result.output
    if output.details is None:
        logger.warning("Agent response missing booking details for request: %s", request)
    if not output.confirmation and output.counter_proposal is None:
        logger.warning("Agent did not provide a counter proposal for request: %s", request)
    payload = output.model_dump(mode="json")
    logger.info(
        "Agent response prepared: confirmation=%s, counter_proposal=%s",
        payload.get("confirmation"),
        payload.get("counter_proposal"),
    )
    sent_emails = deps.mailer.outbox
    if not sent_emails:
        logger.warning("Agent did not send any emails for request: %s", request)
    else:
        logger.info(
            "Agent sent %s email(s) for request: %s", len(sent_emails), request
        )
    summary_payload = {
        "requester_email": email,
        "request": request,
    }
    if summary_payload["requester_email"] == DEFAULT_REQUESTER_EMAIL:
        logger.warning(
            "Agent could not determine a valid requester email for request: %s", request
        )
    return summary_payload, sent_emails


def _interactive_loop() -> None:
    """Run the interactive UI for meeting scheduling."""

    print("Meeting scheduler ready. Type 'exit' to quit.")
    while True:
        try:
            email_input = input("Email> ").strip()
        except EOFError:
            print()
            break
        if email_input.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        try:
            request = input("Request> ").strip()
        except EOFError:
            print()
            break
        if not request:
            continue
        if request.lower() in {"exit", "quit"}:
            print("Goodbye!")
            break
        payload, sent_emails = asyncio.run(_run_agent(email_input, request))
        print(json.dumps(payload, indent=2))
        for email in sent_emails:
            print("Email sent:")
            print(f"To: {email.recipient}")
            print(f"Subject: {email.subject}")
            print("Body:")
            print(email.body)


def main() -> None:
    """Entry point for CLI usage."""

    load_env()
    args = parse_args()
    log_dir = Path(args.log_dir)
    log_file = Path(args.log_file) if args.log_file else _session_log_path(log_dir)
    _configure_logging(log_file)
    _interactive_loop()


if __name__ == "__main__":
    main()
