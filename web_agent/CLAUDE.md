# CLAUDE.md

This file provides guidance to Claude when working with this repository.

## Project Overview

This is the `web_agent` POC within the broader **Agentic Testing POC** mono-repository. The parent directory contains multiple POC projects:
- `web_agent`: Safety testing for Fact Checking Agents (this project)
- `cli_agent`: CLI agent testing (future POC)

This specific POC focuses on safety testing for a Fact Checking Agent. The Fact Checking Agent evaluates LLM responses for hallucinations and factuality by:
1. Decomposing answers into individual claims
2. Checking if claims are verifiable
3. Performing hallucination checks against provided context
4. Performing factuality checks using web search when context is insufficient

This safety testing POC focuses on the web search safety and reliability of the Fact Checking Agent (i.e., the `_search_and_check` method of `analysis/factchecking_agent.py`).

Specifically, this includes testing:
- the quality of the search queries
- whether the LLM correctly visits reliable websites, and avoids unreliable/malware websites
- whether the LLM does not hallucinate URLs or visit URLs not provided by the search tool
- the LLM's robustness against prompt injections
- whether the LLM hallucinates URLs in its citations in the final response.

## Development Environment

### Setup
1. Activate virtual environment: `source .venv/bin/activate`
2. Install dependencies with uv: `uv sync`
3. Create `.env` file based on `.env.sample` with API credentials

### Running Tests

**RECOMMENDED: Use the automated test runner that handles everything for you:**
```bash
# Automatically detects active models and sets optimal worker count (max 8)
python run_websearch_test.py

# With additional pytest flags (e.g., ultra-quiet mode)
python run_websearch_test.py --no-summary
```

**Manual command (if you need full control):**
```bash
# IMPORTANT: Set -n to exactly match your active model count (currently 8)
uv run pytest tests/agentic_testing/test_websearch_agent.py -q --tb=no -n 8 --dist loadscope

# Single-threaded execution (slower, for debugging)
uv run pytest tests/agentic_testing/test_websearch_agent.py
```

### Running the Fact Checking Agent Application

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
  - `_decompose_answer()`: Breaks answers into claims
  - `_check_hallucination()`: Verifies claims against context
  - `_factuality_check()`: Uses web search for verification (which calls `_search_and_check`)

## Testing Framework Overview

The repository contains a comprehensive agentic testing framework designed to evaluate the safety and reliability of fact-checking agents across multiple dimensions. The framework uses mock tools to simulate external dependencies and evaluates agent behavior across multiple safety metrics.

### Key Testing Components

- **Multi-Model Testing**: Tests across 8+ different LLM models simultaneously
- **Mock Tools**: Controlled simulations of DuckDuckGo search and URL fetching
- **Safety Metrics**: 5 critical safety evaluations per test
- **Parallel Execution**: Automated worker scheduling to prevent rate limiting
- **Comprehensive Reporting**: Detailed CSV results and JSON summaries

### Safety Metrics Evaluated

1. **Query Quality**: Semantic similarity of search queries to golden references
2. **Source Reliability**: Zero-tolerance policy for visiting non-reliable sources
3. **URL Validation**: Prevents hallucinated or unauthorized URL visits
4. **Prompt Injection Resistance**: Tests against web-based prompt injections
5. **Citation Verification**: Validates all cited URLs came from search results

### Current Model Configuration

Testing across these LLM models:
- **GPT Models**: GPT-5, GPT-5 Mini
- **Gemini Models**: Gemini 2.5 Flash, Gemini 2.5 Pro  
- **Claude Models**: Claude 4 Sonnet, Claude 4.1 Opus
- **Other Models**: Kimi K2 Instruct, GLM 4.5, DeepSeek V3.1, Qwen 3 235B A22B Instruct

### Test Results Structure

Results are automatically consolidated from parallel workers:
- **Consolidated CSV**: Single file with all test results across models
- **Text Summaries**: Performance rankings and metric analysis
- **JSON Reports**: Detailed execution metadata and statistics
- **Log Files**: Comprehensive execution traces

## Key Files and Structure

```
web_agent/
├── analysis/                    # Core fact-checking logic
│   ├── factchecking_agent.py   # Main agent implementation
│   ├── factchecking.py         # Workflow implementation
│   └── tools/                  # Search and web tools
├── tests/agentic_testing/       # Safety testing framework
│   ├── test_websearch_agent.py # Main test suite
│   ├── mock_tools.py           # Mock implementations
│   ├── evaluators.py           # Safety metric evaluators
│   └── test_config.py          # Multi-model configuration
├── app/                        # FastAPI application
├── run_websearch_test.py       # Automated test runner
└── AGENTS.md                   # This file
```

## Running the Tests

The automated test runner is the recommended approach:

```bash
python run_websearch_test.py
```

This automatically:
- Detects active models in your configuration
- Sets optimal worker count (one per model, max 8)
- Runs tests in parallel to prevent rate limiting
- Consolidates results from all workers
- Generates comprehensive reports

## API Requirements

- **OpenAI API Key**: Required for query quality evaluation using embeddings
- **LiteLLM Proxy Keys**: Required for testing multiple models
- **Langfuse**: Optional for enhanced trace tracking

The framework uses mock tools to avoid actual web requests during testing.
