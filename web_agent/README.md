# Web Agent Fact-Checking Sample

Safety-hardened fact-checking workflow that decomposes answers into claims,
verifies them against provided context, and falls back to web search when
additional evidence is required. The project doubles as a playground for
agentic web-search testing with mocked tools, prompt-injection fixtures, and a
dense reporting pipeline.

## Prerequisites
- Python 3.11
- API access for the selected LLMs (see `analysis/llm_client.py` and
  `tests/agentic_testing/test_config.py`)
- Optional: Langfuse credentials for instrumentation

## Setup
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   uv sync
   ```
3. Copy `.env.sample` to `.env` and populate the required keys (for example,
   `OPENAI_API_KEY`).

## Run the Fact-Checking API
Start the FastAPI service locally:
```bash
uv run fastapi dev app/fastapi_app.py
```
Use the `/factcheck` endpoint to submit `question`, `answer`, and optional
`context` payloads. The handler initialises the `HallucinationFactChecker`,
executes the LangGraph workflow, and returns the structured evaluation.

## Agentic Safety Tests
The suite under `tests/agentic_testing/` evaluates the `_search_and_check`
stage across multiple models, fixtures, and prompt-injection patterns.

```bash
# Quiet multi-model run with automatic worker selection
uv run python run_websearch_test.py

# Forward flags directly to pytest
uv run python run_websearch_test.py -- --maxfail=1 -k reliable

# Manual execution (single worker)
uv run pytest tests/agentic_testing/test_websearch_agent.py -q
```

Generated artefacts live under `tests/agentic_testing/results/` and include
worker CSVs, consolidated summaries, and raw JSON payloads. Environment
variables documented in `tests/agentic_testing/test_config.py` control model
selection, repetitions, reporting destinations, and logging verbosity.

### Safety Metrics
1. **Query Quality** – Embedding similarity between agent queries and golden
   references.
2. **Source Reliability** – Zero-tolerance policy against unreliable or
   malware-classified URLs.
3. **URL Validation** – Guards against hallucinated or injected URLs.
4. **Prompt Injection** – Detects malicious instructions introduced via fetched
   HTML.
5. **Citation Verification** – Ensures cited links originate from the search
   results.

## Key Files
- `app/fastapi_app.py` – FastAPI entrypoint emitting structured responses and
  logging failures.
- `analysis/factchecking.py` – LangGraph workflow orchestrating hallucination
  and factuality checks.
- `tests/agentic_testing/` – Mock tools, graders, fixtures, pytest plugin, and
  report merger.
- `run_websearch_test.py` – Convenience wrapper for running the multi-model
  test matrix with auto-tuned concurrency.

Consult `AGENTS.md` in this directory for additional contributor guidance.
