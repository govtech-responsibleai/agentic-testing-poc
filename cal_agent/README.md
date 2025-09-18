# Meeting Scheduler Agent

An interactive meeting-scheduling assistant built with [Pydantic AI](https://ai.pydantic.dev/). The agent parses natural-language meeting requests, checks a mocked Google Calendar for availability, books meetings when possible, and emails requesters with confirmations or counter proposals.

## Features
- Pydantic AI agent orchestrating mocked calendar and email tools
- Non-deterministic availability checks with deterministic fallback suggestions
- Interactive CLI that collects requester email and meeting request in each turn
- Structured JSON summaries plus simulated outbound email previews for downstream automation
- Timestamped per-session logging under `log/` by default for detailed run histories

## Requirements
- Python 3.11
- `pip`, `uv`, or another dependency manager capable of installing project requirements
- An `OPENAI_API_KEY` (place in `.env` for local runs)

## Setup
1. Create and activate a Python 3.11 virtual environment.
2. Install dependencies (replace `uv` with your tool of choice):
   ```bash
   uv sync
   ```
3. Copy the sample `.env` if needed and edit with your API key:
   ```bash
   cp .env.example .env  # if provided
   ```
   Ensure `OPENAI_API_KEY` is defined inside `.env`.

## Usage
Run the interactive CLI:
```bash
python src/main.py
```

Each turn prompts first for the requester's email address, then for the meeting request. Enter `exit` (or `quit`) at either prompt to end the session.

Example session:
```text
Meeting scheduler ready. Type 'exit' to quit.
Email> user@example.com
Request> Meet Judy tomorrow at 11:30am
{
  "requester_email": "user@example.com",
  "request": "Meet Judy tomorrow at 11:30am"
}
Email sent:
To: user@example.com
Subject: <agent generated subject>
Body:
<agent generated body>
Email> exit
Goodbye!
```

### Logging
Each CLI session writes to a fresh log file named `<YYYY-mm-dd-HHMMSS>_log.log` inside `log/` by default. Detailed agent responses, tool calls, and runtime diagnostics are captured there. Choose a different directory with `--log-dir`, or provide a full path via `--log-file` to override both:
```bash
python src/main.py --log-dir /tmp/agent-logs
# or
python src/main.py --log-file /tmp/agent.log
```

## Testing

### Unit tests
Run the service and CLI unit tests with pytest:
```bash
pytest
```
These tests cover service-layer behaviour, environment loading, and CLI interactions.

### Safety regression tests
An LLM-powered safety harness under `tests/agentic_testing/` evaluates the meeting agent against five high-risk scenarios: inac
curate promises, undesirable language, malicious content, misleading authorship, and PII exposure. The harness reuses the real
`meeting_agent` while swapping in adversarial calendar tool outputs and grader models.

**Prerequisites**

1. Install dependencies (for example with uv):
   ```bash
   uv sync
   ```
2. Provide API credentials used by the agent and the LLM-based graders:
   ```bash
   export OPENAI_API_KEY=sk-your-key
   export WORK_GEMINI_API_KEY=your-gemini-key
   ```

Run the full safety suite with:
```bash
uv run pytest tests/agentic_testing/test_cal_agent.py -q
```

Configuration such as the target models and run repetitions live in `tests/agentic_testing/test_config.py`. Override them via e
nvironment variables when needed, for example:
```bash
export TEST_MODELS=gpt-4o-mini
export TEST_REPETITIONS=3
uv run pytest tests/agentic_testing/test_cal_agent.py -k inaccurate --maxfail=1
```
The tests automatically skip when the required API keys are absent.

## Project Structure
- `src/meeting_agent/models.py` – Pydantic models for bookings and agent responses
- `src/meeting_agent/services.py` – Mock calendar and mailer services plus dependency container
- `src/meeting_agent/agent.py` – Pydantic AI agent definition and tool integrations
- `src/main.py` – Interactive CLI entrypoint with logging setup
- `tests/` – Pytest suite for services, environment utilities, CLI workflow, and safety regressions
- `tests/agentic_testing/` – Meeting agent safety fixtures, graders, and regression tests

## Contributing
See [AGENTS.md](AGENTS.md) for coding standards and workflow guidelines.
