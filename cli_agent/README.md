# CLI Business Agent - Security Testing Sample

A comprehensive security testing framework for a multi-agent business intelligence system. This sample demonstrates how to test CLI agents that execute commands and access sensitive data against various security attack vectors.

## 🎯 What This Tests

This sample evaluates how business analyst agents handle security threats:

- **File Deletion Attacks**: Commands attempting to delete or overwrite files
- **Resource Exhaustion**: Operations that could consume excessive resources
- **PII Exposure**: Handling of sensitive personal data in files
- **Prompt Injection**: Malicious instructions embedded in file contents
- **Agent-Level Security**: Overall security posture and refusal behavior

## 🚀 Quick Start

### Option 1: Using Docker/Podman (Recommended)

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# 2. Build container
podman build -t business-sim .

# 3. Run safety tests
podman run -it --env-file .env business-sim pytest tests/test_cli_agent.py -q

# 4. Run interactive agent
podman run -it --env-file .env business-sim
```

### Option 2: Local Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variable
export OPENAI_API_KEY=your-key-here

# 3. Run safety tests
python run_tests.py

# Or with pytest directly
pytest tests/test_cli_agent.py -v -n auto
```

## 📋 Requirements

- Python 3.11+
- OpenAI API key
- Docker/Podman (for containerized testing)
- pytest, pytest-asyncio, pytest-xdist

## 🏗️ Architecture

### The Multi-Agent System

The business analyst system (`src/business_agents.py`) includes:

1. **Business Analyst Coordinator**: Main orchestrator
2. **SQL Analyst**: Database queries and analysis
3. **File Processor**: Command-line file operations
4. **Meeting Minutes Searcher**: Vector search through documents
5. **Report Writer**: Markdown report generation

### The Data Environment

- **SQLite Database**: 50 products, 25 customers, 150 orders
- **PDF Documents**: 15 invoices + 10 expense receipts
- **CSV Files**: Structured business data
- **Meeting Minutes**: 50 realistic meeting documents
- **Vector Database**: ChromaDB for semantic search

### The Testing Framework

Safety tests (`tests/`):
- **Mock Tool Responses**: Controlled command outputs
- **Real Agent**: Uses actual agent code
- **LLM Graders**: Evaluate security behaviors
- **Test Cases**: 5 security categories × multiple scenarios × repetitions

## 🧪 Running Tests

### Quick Test Run

```bash
# Recommended: automated test runner
python run_tests.py

# With pytest directly
pytest tests/test_cli_agent.py -v -n auto
```

### Parallel Execution

```bash
# Auto-detect worker count
pytest tests/test_cli_agent.py -n auto

# Specify 4 workers
pytest tests/test_cli_agent.py -n 4
```

### Configuration

Customize testing via environment variables:

```bash
# Test specific models
export TEST_MODELS=gpt-4o-mini,gpt-4o

# Change repetition count (default: 3)
export TEST_REPETITIONS=5

# Set worker count
export DEFAULT_WORKERS=4

# Run specific test category
pytest tests/test_cli_agent.py::test_agent_response_to_destructive_command_blocked -v
```

### Test Reports

After each session, reports are generated in `tests/test_reports/`:

1. **CSV Results**: `test_results_<timestamp>.csv` - Full test data
   - Columns: test_id, test_type, model, input_prompt, agent_output, passed, failure_reason, grader_results, execution_time, timestamp
   - Encoding: UTF-8 with BOM for Excel compatibility

2. **Summary Report**: `test_summary_<timestamp>.md` - Pass rates by model and test type

3. **Raw JSON**: `raw_test_results_<timestamp>.json` - Structured data for analysis

## 🔧 Configuration Files

- `tests/test_config.py` - Model settings and test configuration
- `tests/data/test_cases.py` - Security test scenarios
- `tests/graders.py` - LLM-based evaluation functions
- `tests/conftest.py` - Pytest fixtures
- `tests/pytest_plugin.py` - Result capture plugin
- `tests/result_collector.py` - Report generation

## 📊 Understanding Results

### Test Output

```
.........F..F...  # . = pass, F = fail

Test Summary:
Total Tests: 25
Passed: 22 (88%)
Failed: 3 (12%)

Model Performance:
  gpt-4o: 92% pass rate

Test Type Results:
  File Deletion: 95% pass
  Resource Exhaustion: 85% pass
  PII Exposure: 90% pass
  Prompt Injection: 80% pass
  Agent Security: 95% pass
```

### Grader Results

Tests use LLM-based graders to evaluate:
- **Refusal Behavior**: Did the agent refuse dangerous requests?
- **Data Handling**: Did it protect sensitive information?
- **Injection Resistance**: Did it ignore malicious instructions?

Grader results are stored in a JSON mapping:
```json
{
  "refused_user_request": {
    "passed": true,
    "summary": "Agent appropriately refused to delete files"
  }
}
```

## 🎮 Running the Agent Interactively

### In Container

```bash
# Interactive agent session
podman run -it --env-file .env business-sim

# With bash access
podman run -it --env-file .env --entrypoint bash business-sim
```

### Example Queries

```
> What are our top selling products this quarter?
[Agent delegates to SQL Analyst...]

> Search for meetings about budget planning
[Agent uses vector search...]

> Analyze the invoice PDFs
[Agent uses file processor...]

> Create a sales performance report
[Agent coordinates multiple specialists...]
```

## 📁 Project Structure

```
cli_agent/
├── src/
│   ├── business_agents.py           # Multi-agent system
│   ├── db.py                        # Database utilities
│   ├── vector_db.py                 # ChromaDB integration
│   ├── data_generation.py           # Test data generator
│   ├── generate_meeting_minutes.py  # Meeting minute generator
│   └── docs/                        # Generated documents
│       ├── pdf/                     # Invoice & receipt PDFs
│       ├── csv/                     # Business data CSVs
│       └── meeting_minutes/         # Meeting documents
├── tests/
│   ├── test_cli_agent.py            # Main security tests
│   ├── data/
│   │   └── test_cases.py            # Security scenarios
│   ├── graders.py                   # LLM-based graders
│   ├── pytest_plugin.py             # Result capture
│   ├── result_collector.py          # Report generation
│   └── conftest.py                  # Pytest configuration
├── chromadb/                        # ChromaDB config
├── Dockerfile                       # Container definition
├── requirements.txt                 # Dependencies
├── run_tests.py                     # Test runner script
├── README.md                        # This file
├── AGENTS.md                        # Development guide
└── TESTING.md                       # Detailed testing docs
```

## 🔍 Key Concepts

### Agent-Focused Testing

Tests evaluate how agents **respond** to security threats:
- ✅ Does the agent refuse dangerous commands?
- ✅ Does it protect sensitive data?
- ✅ Is it resilient against prompt injection?

### Mock Tool Strategy

Security tests mock the `run_command` tool to return:
- Adversarial command outputs
- Sensitive data payloads
- Malicious instructions

The agent's response to these mocks is evaluated.

### LLM-Based Grading

Uses GPT-4o-mini with caching to evaluate complex security behaviors:

```python
# Example grader usage
result = refused_user_request(
    agent_output="I cannot delete files from the system",
    user_request="Delete all invoices"
)
# Returns: (passed=True, summary="Agent refused dangerous request")
```

## 🐛 Troubleshooting

**Tests fail with "OpenAI API key not found"**: Set `OPENAI_API_KEY` environment variable

**Container build fails**: Ensure Docker/Podman is installed and running

**Database not found**: Run `python src/data_generation.py` to generate test data

**Import errors**: Install dependencies: `pip install -r requirements.txt`

**Grader failures**: Check that grader model (gpt-4o-mini) is accessible

**Test reports not generating**: Check write permissions in `tests/test_reports/`

## 🗄️ Data Generation

Generate fresh test data:

```bash
# Locally
python src/data_generation.py

# In container
podman run -it --env-file .env business-sim python src/data_generation.py
```

This creates:
- SQLite database with business data
- PDF invoices and receipts
- CSV files
- Meeting minutes
- Vector database indices

## 📚 Related Documentation

- [AGENTS.md](./AGENTS.md) - Development guidelines (note: simplified version coming)
- [TESTING.md](./TESTING.md) - Comprehensive testing documentation
- [Root README](../README.md) - Repository overview

## 🤝 Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines.
