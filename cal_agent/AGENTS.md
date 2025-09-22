# Meeting Scheduler Agent Testing Guide

This directory hosts both the interactive meeting scheduler agent and its agentic safety regression suite. The guidance below explains how to work on the agent implementation and how to run the associated tests.

## Project Overview
- **Agent**: Pydantic AI powered assistant that books meetings by coordinating mocked calendar and email tools.
- **Safety tests**: Pytest-based harness under `tests/agentic_testing/` that exercises the real agent against five high-risk calendar tool scenarios using LLM graders.
- **Goal**: Ensure the agent refuses unsafe instructions injected through the calendar tool while remaining helpful for legitimate scheduling tasks.

## Setup
1. Use **Python 3.11**.
2. Install dependencies (example with uv):
   ```bash
   uv sync
   ```
3. Copy or create a `.env` file that defines the required API keys:
   ```bash
   export OPENAI_API_KEY=sk-your-key
   export WORK_GEMINI_API_KEY=your-gemini-key
   ```
4. Activate logging/output directories as needed; never commit secrets.

## Running the Meeting Agent
```bash
uv run python src/main.py
```
The CLI collects the requester email and the meeting request each turn. Logs are written to the `log/` directory unless overwritten via CLI flags.

## Safety Testing Framework

### Quick start
Run the safety suite with the default model configuration (single worker):
```bash
uv run pytest tests/agentic_testing/test_cal_agent.py -q
```
Tests automatically skip when `OPENAI_API_KEY` or `WORK_GEMINI_API_KEY` is missing. `pydantic_ai` must also be importable.

Rate limits from upstream providers can cause intermittent `429` or "quota" failures. The regression tests automatically retry these failures with delays of 10, 30, 60, and 60 seconds (five total attempts) before surfacing an error, mirroring the CLI agent suite's resilience logic.

To parallelise, enable xdist workers—the reporting plugin merges runs from all workers automatically:
```bash
uv run pytest tests/agentic_testing/test_cal_agent.py -v -n auto
```

### Configuration & repetitions
- Default options live in `tests/agentic_testing/test_config.py`.
- Override at runtime via environment variables, for example:
  ```bash
  export CAL_AGENT_TEST_MODELS=gpt-4o-mini
  export CAL_AGENT_TEST_REPETITIONS=2
  uv run pytest tests/agentic_testing/test_cal_agent.py -k inaccurate --maxfail=1
  ```
- Tests call the real `meeting_agent` from `src/meeting_agent/agent.py` with mocked calendar responses defined in `tests/agentic_testing/data/test_cases.py`.

### Session reporting
- The pytest plugin under `tests/agentic_testing/pytest_plugin.py` captures prompts, agent outputs, grader payloads, execution timing, and error metadata for every run (including failures).
- Aggregated artefacts are written to `tests/agentic_testing/test_reports/` at session end:
  - `test_results_<timestamp>.csv` – consolidated row-level results (UTF-8 with BOM for spreadsheet use)
  - `test_summary_report_<timestamp>.md` – human-readable pass/fail overview and failed-test highlights
  - `raw_test_results_<timestamp>.json` – structured payload for downstream analysis
- Per-worker scratch files named `worker_<session>_*.json` exist during execution and are removed once the consolidated reports are generated. Generated artefacts are ignored via the directory’s `.gitignore`; do not commit them.
- Control report emission with environment variables defined in `test_config.py`, e.g. set `CAL_AGENT_GENERATE_REPORTS=0` to disable reporting or `CAL_AGENT_REPORTS_DIR=/tmp/cal_agent_reports` to change the destination.

### Risk categories
The fixtures cover five adversarial behaviours:
1. **Inaccurate promises** – calendar tool urges the agent to make misleading public commitments.
2. **Undesirable language** – prompts attempt to insert profanity or abusive tone.
3. **Malicious content** – instructions push suspicious links or malware-style copy.
4. **Misleading authorship** – attempts to impersonate senior officials in sign-offs.
5. **PII exposure** – responses include sensitive personal data leaked by the tool.

Grading is handled by `tests/agentic_testing/graders.py`, which relies on LLM judges. New scenarios should follow the existing `CalendarInjectionCase` structure.

## Contribution Guidelines
- Follow **PEP 8** and include **type hints** for all functions and methods.
- Sort imports alphabetically within standard-library, third-party, and local groups.
- Prefer **f-strings** and the **logging** module over raw `print` statements.
- Document public modules, classes, and functions with docstrings.
- Run `pytest` before submitting changes; ensure deterministic behaviour in tests by mocking randomness when necessary.
- Keep dependencies minimal and update this guide plus `README.md` whenever configuration expectations change.

These rules extend the root-level `AGENTS.md`. When conflicts arise, prefer the more specific instructions in this file.
