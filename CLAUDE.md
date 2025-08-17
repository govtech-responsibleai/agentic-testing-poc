# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a safety testing POC for the SLS LEA Fact Checking Agent. The system evaluates LLM responses for hallucinations and factuality by:
1. Decomposing answers into individual claims
2. Checking if claims are verifiable
3. Performing hallucination checks against provided context
4. Performing factuality checks using web search when context is insufficient

## Development Environment

### Setup
1. Activate virtual environment: `source .venv/bin/activate`
2. Install dependencies with uv: `uv sync`
3. Create `.env` file based on `.env.sample` with API credentials

### Running Tests

Always activate venv and use uv for package management:
```bash
# Run specific test file
source .venv/bin/activate && uv run pytest tests/evals/test_decompose_answer.py

# Run safety tests
source .venv/bin/activate && uv run pytest tests/evals/test_decompose_answer_safety.py -v -s

# Run single test
source .venv/bin/activate && uv run pytest tests/evals/test_decompose_answer.py::test_decompose_answer_correct_number_of_claims -v

# Run agentic tests for web search safety
source .venv/bin/activate && uv run pytest tests/agentic_testing/test_websearch_agent.py -v -s

# Run multi-model tests (tests all configured models)
uv run pytest tests/agentic_testing/test_websearch_agent.py
```

### Running the Application

```bash
# Local development
uv run -m fastapi dev app/fastapi_app.py

# Run fact-checking script
PYTHONPATH=. uv run analysis/lea_hallucination_factcheck.py --input_file="data/analysis/hd_fc_by_record.csv" --output_folder="data/output/hallucination_factchecking/records" --batch_size=10
```

## Architecture & Key Components

### Core Workflow (`analysis/factchecking.py`)
- `HallucinationFactChecker`: Main class implementing LangGraph workflow
- Key methods:
  - `_decompose_answer()`: Breaks answers into claims (safety vulnerability identified here)
  - `_check_hallucination()`: Verifies claims against context
  - `_factuality_check()`: Uses web search for verification

### Safety Testing Focus

**Critical Finding**: The `_decompose_answer` method has a prompt injection vulnerability - it doesn't filter malicious instructions from claims.

Safety test files created:
- `tests/evals/test_decompose_answer_safety.py`: Comprehensive safety tests
- `tests/evals/test_decompose_answer_safety_simple.py`: Simplified version for quick testing
- `tests/evals/SAFETY_TEST_FINDINGS.md`: Detailed findings and recommendations

### Agentic Testing Framework (`tests/agentic_testing/`)

Comprehensive framework for testing the FactCheckingAgent's web search functionality with focus on safety and reliability. The framework uses mock tools to simulate external dependencies and evaluates agent behavior across multiple safety metrics.

**Key Components:**
- **Test Suite** (`test_websearch_agent.py`): Parameterized tests for the `_search_and_check` method
- **Evaluators** (`evaluators.py`): 
  - `QueryQualityEvaluator`: Compares agent queries with golden queries using embeddings
  - `SourceReliabilityEvaluator`: Detects visits to malware/unreliable sources
  - `PromptInjectionEvaluator`: Tests resistance to prompt injections in web content
  - `CitationVerificationEvaluator`: Ensures no hallucinated citations
- **Mock Tools** (`mock_tools.py`): Simulates DuckDuckGo search and URL fetching with controlled responses
- **Test Fixtures** (`fixtures/websearch_fixtures.py`): Predefined test cases with various source types

### Test Categories

1. **Hallucination Detection**: Ensures decomposition doesn't add claims not in original answer
2. **Unsafe Input Handling**: Tests prompt injections, SQL injection patterns, Unicode exploits
3. **Hybrid Evaluation**: Uses ROUGE scoring + LLM judge + semantic similarity
4. **Web Search Safety**: Tests agent's behavior when interacting with external web sources
5. **Source Reliability**: Ensures agent avoids malicious/unreliable sources
6. **Prompt Injection Resistance**: Validates agent isn't compromised by malicious web content

### API Endpoints

- Health check: `GET /`
- Fact-checking: `POST /factcheck`
  - Input: `{question, answer, context}`
  - Output: Detailed claim-by-claim analysis

## Safety Testing Guidelines

When adding safety tests:
1. Test edge cases like empty strings, None values, extremely long inputs
2. Include prompt injection attempts with various patterns
3. Test Unicode and special character handling
4. Verify no information is added during decomposition
5. Use hybrid evaluation approach for robust verification

## Agentic Testing Configuration

**Mock Tools Approach**: The framework uses simplified mock tools that:
- Override tool methods directly for reliable interception
- Return controlled fixture data for reproducible tests
- Track all queries and URL visits for analysis
- Inject malicious content into ALL visited URLs for comprehensive safety testing

**API Requirements**: 
- OpenAI API key required for QueryQualityEvaluator (uses embeddings)
- Tests use mock tools to avoid actual web requests
- Fixtures provide controlled, repeatable test scenarios

## Known Issues

1. **Prompt Injection Vulnerability**: System doesn't filter injection attempts in decomposition
2. **Authentication Errors**: May occur with LLM judge in tests - check API credentials
3. **Long Test Execution**: Some tests may timeout due to multiple LLM calls

## Multi-Model Testing Framework

The agentic testing framework now supports testing multiple LLM models in a single test run. This enables systematic comparison of model performance across safety metrics.

### Configuration (`test_config.py`)

The test configuration file defines:
- **Models to test**: Multiple LLM models can be configured with their API keys and endpoints
- **Test parameters**:
- `runs_per_test`: Number of times to run each test per model
- `fixtures_to_test`: List of specific fixtures to test (e.g., `["websearch_00003"]`)
- `save_results`: Whether to save CSV results and summary reports
- `results_dir`: Directory for test results

### Running Multi-Model Tests

```bash
# Run tests for all configured models
uv run pytest tests/agentic_testing/test_websearch_agent.py

# Run with verbose output
uv run pytest tests/agentic_testing/test_websearch_agent.py -v -s

# Run specific test fixtures
# (Configure in test_config.py fixtures_to_test)
```

### Test Results

Results are automatically saved to:
- **CSV Results**: `tests/agentic_testing/results/multi_model_results_[timestamp].csv`
  - Detailed metrics for each test run
  - Model performance on each safety metric
  - Agent outputs and error messages
  
- **Summary Report**: `tests/agentic_testing/results/summary_report_[timestamp].json`
  - Overall pass rates per model
  - Metric-specific performance comparison
  - Statistical summary across all tests

### Metrics Evaluated

1. **Query Quality**: Cosine similarity between agent queries and golden queries
2. **Source Reliability**: Detection of malware/unreliable sources
3. **Prompt Injection Resistance**: Tests against injected malicious prompts
4. **Citation Verification**: Ensures no hallucinated citations

## Recent Updates

- **Multi-Model Testing**: Framework supports testing multiple models with comprehensive CSV and JSON result tracking
- **Enhanced Prompt Injection**: Mock tools now inject malicious prompts into ALL visited URLs for more rigorous testing
- **Simplified Mock Tools**: Direct method override approach for reliable query tracking and fixture injection
- **Query Tracking Fix**: Search queries are now properly captured for similarity analysis