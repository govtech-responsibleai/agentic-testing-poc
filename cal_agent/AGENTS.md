# Meeting Scheduler Agent - Development Guide

Development guidelines specific to the meeting scheduler agent testing sample.

## Project Overview

- **Agent**: Pydantic AI powered meeting scheduler with mocked calendar and email tools
- **Safety Tests**: Pytest suite testing agent responses to adversarial calendar tool outputs
- **Goal**: Ensure agents refuse unsafe instructions while remaining helpful for legitimate tasks

## Quick Commands

```bash
# Run the agent
uv run python src/main.py

# Run unit tests
uv run pytest tests/ -k "not agentic_testing"

# Run safety tests
uv run pytest tests/agentic_testing/test_cal_agent.py -q

# Parallel safety tests
uv run pytest tests/agentic_testing/test_cal_agent.py -n auto
```

## Development Standards

Extends root [AGENTS.md](../AGENTS.md) with project-specific rules:

### Python Version
- **Python 3.11** (same as root)

### Dependencies
- Use `uv` for package management
- Keep dependencies minimal
- Update requirements when adding packages

### Code Style
- Follow PEP 8 conventions
- Include type hints for all functions
- Sort imports alphabetically (stdlib, third-party, local)
- Prefer f-strings for formatting
- Use `logging` module instead of `print`

### Testing

#### Unit Tests
- Test service layer independently
- Test environment loading
- Test model validation
- Mock external dependencies

#### Safety Tests
- Add new scenarios to `tests/agentic_testing/data/test_cases.py`
- Follow `CalendarInjectionCase` structure
- Include clear descriptions and expected behaviors
- Test against all configured models

### Safety Test Framework

#### Adding New Test Scenarios

1. Define case in `tests/agentic_testing/data/test_cases.py`:

```python
NEW_RISK_CASES = [
    CalendarInjectionCase(
        test_id="new_risk_001",
        category="new_risk_category",
        description="Description of the attack",
        request_text="User request text",
        adversarial_response="Malicious instruction from calendar tool",
        expected_behavior="How agent should respond"
    )
]
```

2. Add grader function to `tests/agentic_testing/graders.py`:

```python
async def detects_new_risk(agent_output: str, expected_behavior: str) -> tuple[bool, str]:
    """Evaluate if agent handles new risk appropriately."""
    # Use LLM-based evaluation
    # Return (passed, reasoning)
```

3. Add test function to `tests/agentic_testing/test_cal_agent.py`:

```python
@rate_limit_retry
@capture_test_results
async def test_agent_response_to_new_risk(model: str, case: CalendarInjectionCase):
    # Test implementation
```

#### Grader Guidelines

- Use LLM-based grading for nuanced behaviors
- Provide clear prompts to grader models
- Return `(bool, str)` tuple: (passed, reasoning)
- Handle edge cases gracefully
- Cache grader results when possible

### Configuration

- Test configuration: `tests/agentic_testing/test_config.py`
- Environment variables:
  - `CAL_AGENT_TEST_MODELS`: Comma-separated model list
  - `CAL_AGENT_TEST_REPETITIONS`: Number of runs per test
  - `CAL_AGENT_GENERATE_REPORTS`: Enable/disable reporting
  - `CAL_AGENT_REPORTS_DIR`: Custom report directory

### Logging

- Agent logs: `log/<timestamp>_log.log`
- Test logs: Captured by pytest
- Use structured logging for important events
- Include context in log messages

### Rate Limiting

Safety tests include automatic retry logic:
- Retry delays: 10s, 30s, 60s, 60s (5 attempts total)
- Detects: HTTP 429, "rate limit", "quota" errors
- Decorator: `@rate_limit_retry`

### Reporting

Pytest plugin automatically generates:
- CSV results with full metadata
- Markdown summary with pass rates
- Raw JSON for analysis

Reports include:
- Test execution details
- Agent outputs
- Grader results
- Timing information
- Failure reasons

### Best Practices

#### Agent Development

- Keep instructions clear and concise
- Use structured outputs (Pydantic models)
- Tool calls should be explicit and traceable
- Handle tool errors gracefully
- Log important decisions

#### Test Development

- One test category per test function
- Use parametrization for multiple scenarios
- Mark async tests with `pytest.mark.asyncio`
- Use fixtures for common setup
- Clean up resources in teardown

#### Documentation

- Update README for user-facing changes
- Document new test scenarios clearly
- Include examples in docstrings
- Keep AGENTS.md current with workflow changes

## Troubleshooting

**Import errors**: Run `uv sync`

**API key missing**: Set `OPENAI_API_KEY` and `WORK_GEMINI_API_KEY`

**Rate limits**: Reduce parallelism or increase retry delays

**Report generation fails**: Check write permissions in `test_reports/`

**Tests not discovered**: Ensure files match `test_*.py` pattern

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for general guidelines.

Project-specific considerations:
- Test new features against adversarial scenarios
- Maintain backwards compatibility with existing graders
- Document breaking changes clearly
- Run full test suite before submitting PRs
