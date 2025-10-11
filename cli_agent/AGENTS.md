# CLI Business Agent - Development Guide

Development guidelines specific to the CLI business agent security testing sample.

## Project Overview

- **Agent System**: Multi-agent business intelligence system with SQL, file processing, vector search, and reporting capabilities
- **Security Tests**: Pytest suite testing agent responses to command injection, PII exposure, and prompt injection attacks
- **Goal**: Ensure agents handle sensitive operations securely and refuse dangerous requests

## Quick Commands

```bash
# Build container
podman build -t business-sim .

# Run agent interactively
podman run -it --env-file .env business-sim

# Run security tests
podman run -it --env-file .env business-sim pytest tests/test_cli_agent.py -q

# Local testing (without container)
python run_tests.py

# Generate test data
python src/data_generation.py
```

## Development Standards

Extends root [AGENTS.md](../AGENTS.md) with project-specific rules:

### Python Version
- **Python 3.11** (same as root)

### Dependencies
- Use `pip` or `uv` for package management
- Container uses pip + requirements.txt
- Keep dependencies minimal
- Document why each dependency is needed

### Code Style
- Follow PEP 8 conventions
- Include type hints for all functions
- Sort imports alphabetically (stdlib, third-party, local)
- Prefer f-strings for formatting
- Use `logging` module instead of `print`

### Architecture

#### Multi-Agent System

Five specialized agents in `src/business_agents.py`:

1. **Business Analyst Coordinator**: Routes queries to specialists
2. **SQL Analyst**: Database queries with `query_database` tool
3. **File Processor**: Command execution with `run_command` tool (security-critical)
4. **Meeting Minutes Searcher**: Vector search with `search_meeting_minutes` tool
5. **Report Writer**: Markdown generation with `write_report` tool

#### Security Model

- **Allowlist approach**: Only specific commands permitted
- **Sandboxed execution**: Limited to `/app/src/docs` directory
- **Timeout protection**: 10-second command timeout
- **Mock testing**: Security tests mock tool responses to evaluate agent behavior

### Testing

#### Unit Tests (if added)
- Test individual agent tools
- Mock database and file system
- Test error handling
- Validate data generation

#### Security Tests (`tests/test_cli_agent.py`)

Five security test categories:

1. **File Deletion**: `test_agent_response_to_destructive_command_blocked`
2. **Resource Exhaustion**: `test_agent_response_to_resource_exhaustion_blocked`
3. **PII Exposure**: `test_agent_response_to_pii_data_exposure`
4. **Prompt Injection**: `test_agent_response_to_prompt_injection`
5. **Agent Security**: Additional security scenarios

Each test:
- Mocks tool responses with adversarial content
- Runs real agent code
- Uses LLM graders to evaluate behavior
- Runs multiple times (repetitions) across models

### Security Test Framework

#### Adding New Test Scenarios

1. Define test cases in `tests/data/test_cases.py`:

```python
NEW_SECURITY_CASES = [
    {
        "command": "new dangerous command",
        "description": "Why this is dangerous",
        "expected_behavior": "Agent should refuse"
    }
]
```

2. Add to existing test function or create new one:

```python
@pytest.mark.parametrize("model", TEST_MODELS)
@pytest.mark.parametrize("test_case", NEW_SECURITY_CASES)
async def test_new_security_category(model, test_case):
    _configure_model_client(model)

    with patch.object(ba, 'run_command', return_value=test_case['mock_output']):
        agent_output = await run_agent(test_case['command'])

    passed, summary = await grader_function(agent_output, test_case['expected_behavior'])
    assert passed, summary
```

3. Add grader to `tests/graders.py` if needed:

```python
async def new_security_grader(agent_output: str, expected: str) -> tuple[bool, str]:
    """Evaluate new security behavior."""
    # Use LLM-based evaluation with gpt-4o-mini
    # Return (passed, reasoning)
```

#### Grader Guidelines

- Use `gpt-4o-mini` for LLM-based grading
- Enable response caching for efficiency
- Return `(bool, str)`: (passed, reasoning)
- Store results in `grader_results` JSON mapping
- Handle edge cases gracefully

### Configuration

- Test configuration: `tests/test_config.py`
- Environment variables:
  - `TEST_MODELS`: Comma-separated model list
  - `TEST_REPETITIONS`: Runs per test (default: 3)
  - `DEFAULT_WORKERS`: Worker count for parallel execution
  - `OPENAI_API_KEY`: Required for agents and graders

### Test Runner

`run_tests.py` provides convenient test execution:

```bash
# Default settings
python run_tests.py

# Custom configuration
python run_tests.py --repetitions 5 --models gpt-4o-mini --workers 4

# Quick status check
python run_tests.py --quick
```

### Logging

- Agent logs: Captured by OpenAI Agents SDK
- Test logs: pytest output
- Use structured logging for important events
- Include test_id and test_type in metadata

### Reporting

Pytest plugin generates reports in `tests/test_reports/`:

1. **CSV Results**: Full test data with columns:
   - test_id, test_type, run_num, model
   - input_prompt, agent_output
   - passed, failure_reason
   - grader_results (JSON mapping)
   - execution_time, timestamp

2. **Summary Markdown**: Pass rates by model and test type

3. **Raw JSON**: Structured data for analysis

CSV files use UTF-8 with BOM for Excel compatibility.

### Data Generation

`src/data_generation.py` creates:
- SQLite database with business data
- PDF invoices and receipts (using ReportLab)
- CSV files with structured data
- Meeting minutes (using Faker)
- Vector database indices (ChromaDB)

Run after modifying data schemas or adding new document types.

### Docker/Podman

Dockerfile provides isolated testing environment:
- Pre-downloads embedding models
- Generates all test data during build
- Exposes agent on container startup
- Includes all dependencies

### Best Practices

#### Agent Development

- Keep agent instructions clear and specific
- Use OpenAI Agents SDK handoff patterns
- Validate tool inputs before execution
- Handle tool errors gracefully
- Log important agent decisions

#### Tool Development

- Minimize attack surface (allowlist, not blocklist)
- Validate all inputs
- Use timeouts for external operations
- Return structured error messages
- Test error paths thoroughly

#### Test Development

- One security category per test function
- Use async/await for agent calls
- Mock tool responses for controlled scenarios
- Test both refusal and safe handling
- Include test_id and test_type in metadata

#### Documentation

- Update README for user-facing changes
- Document new test scenarios clearly
- Include security implications
- Keep examples current

## Troubleshooting

**Container build fails**: Check Docker/Podman installation and disk space

**Database not found**: Run `python src/data_generation.py`

**Import errors**: Install dependencies: `pip install -r requirements.txt`

**API key errors**: Set `OPENAI_API_KEY` environment variable

**Grader failures**: Check gpt-4o-mini is accessible

**Report generation fails**: Check write permissions in `tests/test_reports/`

**Async test errors**: Ensure pytest-asyncio is installed

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for general guidelines.

Project-specific considerations:
- Test new features against security attack vectors
- Maintain allowlist-based security model
- Document security assumptions clearly
- Run full test suite before submitting PRs
- Consider containerized testing for consistency
