# Agentic Testing Samples

This repository bundles three self-contained projects that demonstrate how to
build and test agentic workflows. Each sample focuses on a different interface
while sharing common expectations for Python 3.11, type hints, logging, and
pytest-based verification.

## Projects
- **`cal_agent`** – Meeting scheduler driven by Pydantic AI with a CLI and an
  LLM-assisted safety regression harness.
- **`cli_agent`** – Business-analytics multi-agent system showcasing file and
  database tooling plus a concurrent safety test runner.
- **`web_agent`** – Fact-checking workflow that stresses web-search safety and
  hallucination detection through an agentic test matrix.

Each directory provides its own `README.md` with setup instructions, execution
tips, and safety test guidance. Start from the project that best matches the
interface you want to explore.

## Prerequisites
- Python 3.11
- `uv` or another dependency manager capable of installing project
  requirements
- Access to the API keys referenced in the project-specific READMEs (e.g.,
  `OPENAI_API_KEY`)

## Repository Layout
- `AGENTS.md` – Shared contribution rules and coding standards.
- `cal_agent/` – Meeting scheduler agent, CLI entrypoint, pytest safety suite.
- `cli_agent/` – Multi-agent CLI system, mock business dataset, safety runner.
- `web_agent/` – Fact-checking web agent, FastAPI app, web-search evaluation
  harness.

## Working Across Projects
1. Read `AGENTS.md` and the project-level `AGENTS.md` for local guidelines.
2. Create an isolated virtual environment per project and sync dependencies.
3. Follow the project README for running the agent and its safety tests.
4. Keep generated artefacts (logs, reports) out of version control.

When publishing or demonstrating the samples, highlight the contrasts between
CLI, calendar, and web-search testing so viewers can see how consistent safety
principles apply across different agent surfaces.
