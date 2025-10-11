# CLI Agent Safety Sample

Business-oriented multi-agent system that demonstrates how to exercise a CLI
assistant with structured safety tests. The coordinator delegates to
specialised agents for SQL analysis, command-line file inspection, meeting
minutes search, and Markdown report writing. A mocked dataset (SQLite, PDFs,
CSVs, and vector embeddings) is bundled to keep evaluation self-contained.

## Prerequisites
- Python 3.11
- OpenAI-compatible API key (set `OPENAI_API_KEY`)
- Optional: LiteLLM or Hugging Face keys when expanding the model matrix

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Copy the example environment file and provide secrets:
   ```bash
   cp .env.example .env
   ```
   Populate `OPENAI_API_KEY` and any additional keys required by
   `tests/test_config.py`.

## Run the Agent
Launch the interactive business analyst workflow:
```bash
uv run python -m src.business_agents
```
You can pick from the configured models, interact over multiple turns, and
inspect streamed responses from the specialist agents. Reports created by the
Report Writer are saved under `/app/output_reports/` when running inside the
container, or alongside the repo when executed locally.

Container usage (optional):
```bash
podman build -t business-sim .
podman run -it --env-file .env business-sim
```

## Safety Testing
The `run_tests.py` helper wraps the pytest safety suite with model selection,
repetition counts, parallel workers, and automated report generation.

```bash
# Default configuration from tests/test_config.py
uv run python run_tests.py

# Custom selection
uv run python run_tests.py --models gpt-5-mini gpt-5-nano --repetitions 2 --workers auto

# Skip consolidated reports when iterating quickly
uv run python run_tests.py --no-reports -q
```

Pytest artefacts are written to `tests/test_reports/`:
- CSV (`test_results_<timestamp>.csv`)
- Markdown summary (`test_summary_report_<timestamp>.md`)
- Raw JSON (`raw_test_results_<timestamp>.json`)

Override the destination by exporting `TEST_REPORTS_DIR`. Safety metrics cover
destructive command refusal, resource exhaustion, PII handling, prompt
injection resistance, and overall agent compliance.

## Key Files
- `src/business_agents.py` – Multi-agent coordinator, tool definitions, and CLI
  loop.
- `src/db.py` – Typed helper functions for the SQLite sample database.
- `src/vector_db.py` – Chroma-backed semantic search over meeting minutes.
- `run_tests.py` – Logging-aware wrapper around the safety test suite.
- `tests/` – Agentic safety fixtures, LLM graders, pytest plugins, and report
  collectors.

Refer to `AGENTS.md` in this directory for coding standards that extend the
root guidelines.
