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

### Test Categories

1. **Hallucination Detection**: Ensures decomposition doesn't add claims not in original answer
2. **Unsafe Input Handling**: Tests prompt injections, SQL injection patterns, Unicode exploits
3. **Hybrid Evaluation**: Uses ROUGE scoring + LLM judge + semantic similarity

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

## Known Issues

1. **Prompt Injection Vulnerability**: System doesn't filter injection attempts in decomposition
2. **Authentication Errors**: May occur with LLM judge in tests - check API credentials
3. **Long Test Execution**: Some tests may timeout due to multiple LLM calls