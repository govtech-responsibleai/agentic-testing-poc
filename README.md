# Agentic Testing POC

A comprehensive repository demonstrating three distinct approaches to safety testing for AI agents. This project showcases practical implementations of "agentic testing" - using LLMs to evaluate LLM agent behavior across critical safety dimensions.

## Overview

As AI agents become more autonomous and capable, ensuring their safety and reliability is paramount. Traditional testing approaches often fall short when dealing with the nuanced, context-dependent behavior of LLM-powered agents. This repository presents three real-world examples of **agentic testing** - leveraging LLMs themselves to evaluate agent outputs for safety violations, prompt injection resistance, data handling compliance, and more.

### What is Agentic Testing?

Agentic testing uses LLMs as evaluators ("graders" or "judges") to assess agent behavior against safety policies that are difficult to encode in traditional tests. Instead of writing rigid assertions, agentic tests:

- **Present adversarial scenarios** to the agent under test
- **Mock external dependencies** with controlled, potentially malicious outputs
- **Evaluate agent responses** using LLM judges that understand context and nuance
- **Generate comprehensive reports** tracking safety metrics across multiple runs

This approach is particularly valuable for testing:
- Prompt injection resistance
- PII and sensitive data handling
- Response to malicious tool outputs
- Citation accuracy and source reliability
- Refusal of inappropriate requests

## The Three Testing Approaches

This repository contains three independent agent implementations, each demonstrating different aspects of agentic testing:

### 1. [Meeting Scheduler Agent](cal_agent/) - Policy Compliance Testing
**Agent Type**: Pydantic AI meeting scheduling assistant  
**Testing Focus**: Adversarial calendar tool responses and output safety

Tests how a meeting scheduling agent responds when calendar tools inject:
- Inaccurate promises and commitments
- Undesirable language (profanity, offensive content)
- Malicious content (phishing links, malware prompts)
- Misleading authorship claims
- PII exposure in responses

**Key Features**:
- Mocked calendar and email services
- LLM-based graders for nuanced policy evaluation
- Parallel test execution with xdist
- Comprehensive CSV/JSON/Markdown reporting

[→ Read more about the Meeting Scheduler Agent](cal_agent/README.md)

### 2. [CLI Agent](cli_agent/) - Command Execution Safety
**Agent Type**: OpenAI Agents SDK multi-agent business assistant  
**Testing Focus**: Safe command execution and data handling

Tests a business analysis agent system's ability to safely handle:
- File deletion and destructive command attempts
- Resource exhaustion attacks
- PII exposure from files and databases
- Prompt injection via file contents

**Key Features**:
- Multi-agent architecture with specialized analysts
- Mocked tool responses simulating malicious outputs
- Docker-containerized testing environment
- SQLite and vector DB integrations

[→ Read more about the CLI Agent](cli_agent/README.md)

### 3. [Web Search Fact-Checking Agent](web_agent/) - Web Safety Testing
**Agent Type**: LangGraph fact-checking agent with web search  
**Testing Focus**: Safe web search and source reliability

Tests a fact-checking agent across 5 critical safety metrics:
- **Query Quality**: Search query appropriateness
- **Source Reliability**: Avoiding malicious/unreliable websites
- **URL Validation**: Preventing hallucinated URLs
- **Prompt Injection**: Resistance to web-based attacks
- **Citation Verification**: Accurate source attribution

**Key Features**:
- Mock DuckDuckGo search and URL fetching tools
- Multi-model testing framework (8+ LLMs)
- Comprehensive evaluators with OpenAI embeddings
- Detailed execution traces via Langfuse

[→ Read more about the Web Search Agent](web_agent/README.md)

## Repository Structure

```
agentic-testing-poc/
├── cal_agent/          # Meeting Scheduler Agent (Pydantic AI)
│   ├── src/            # Agent implementation
│   ├── tests/          # Unit and safety tests
│   └── README.md       # Detailed documentation
│
├── cli_agent/          # CLI Agent (OpenAI Agents SDK)
│   ├── src/            # Multi-agent system
│   ├── tests/          # Security safety tests
│   └── README.md       # Detailed documentation
│
├── web_agent/          # Web Search Fact-Checking Agent (LangGraph)
│   ├── analysis/       # Fact-checking workflow
│   ├── tests/          # Multi-model safety tests
│   └── README.md       # Detailed documentation
│
├── AGENTS.md           # Coding standards and guidelines
└── README.md           # This file
```

## Prerequisites

All three agents require:

- **Python 3.11** or higher
- API keys for LLM providers (OpenAI, Gemini, etc.)
- Basic familiarity with pytest and async Python

Each agent has specific dependencies - see individual README files for details.

## Quick Start

Each agent can be tested independently:

### Meeting Scheduler Agent
```bash
cd cal_agent
uv sync  # Install dependencies
export OPENAI_API_KEY=your-key
uv run pytest tests/agentic_testing/test_cal_agent.py -v
```

### CLI Agent
```bash
cd cli_agent
podman build -t business-sim .
podman run -it --env-file .env business-sim
pytest tests/test_cli_agent.py -v -n auto
```

### Web Search Agent
```bash
cd web_agent
uv sync
python run_websearch_test.py  # Automated multi-model testing
```

## Key Concepts

### Mocked Tools
All three implementations use **mock tools** to simulate external dependencies with controlled outputs. This allows testing how agents respond to:
- Malicious data from APIs
- Prompt injection attempts
- PII in tool responses
- Rate limits and errors

### LLM Graders
Safety evaluation uses LLM judges that understand:
- **Policy compliance** (did the agent refuse appropriately?)
- **PII detection** (did the agent expose sensitive data?)
- **Prompt injection** (was the agent manipulated?)
- **Citation accuracy** (are sources real and properly attributed?)

### Comprehensive Reporting
Each testing framework generates:
- **CSV results** with per-test metadata and scores
- **JSON payloads** with full agent outputs and grader reasoning
- **Markdown summaries** with pass rates and failure analysis

## Testing Philosophy

### Agent-Focused Testing
Tests evaluate the **agent's behavior and outputs**, not just individual tools. This captures emergent issues that arise from agent reasoning, tool orchestration, and output generation.

### Adversarial by Design
Test fixtures are intentionally adversarial, simulating:
- Compromised APIs
- Malicious web content
- Social engineering attempts
- Data exfiltration scenarios

### Statistical Rigor
Tests run multiple times per scenario to detect:
- Non-deterministic failures
- Edge cases
- Model-specific vulnerabilities

## Contributing

See [AGENTS.md](AGENTS.md) for:
- Code style guidelines (PEP8, type hints, docstrings)
- Testing standards
- PR conventions

Each agent also has its own `AGENTS.md` with specific guidance.

## License

This project is intended for educational and research purposes, demonstrating practical approaches to AI agent safety testing.

## Acknowledgments

These implementations draw on emerging best practices in AI safety, including work on:
- Red teaming LLM applications
- Adversarial robustness testing
- Prompt injection prevention
- AI agent monitoring and observability
