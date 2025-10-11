# Agentic Testing Samples

This repository contains three comprehensive examples of safety and security testing for AI agents. Each sample demonstrates best practices for evaluating agent behavior across different risk scenarios using LLM-based grading and systematic test frameworks.

## 📦 Samples

### 1. [Meeting Scheduler Agent](./cal_agent/) - Calendar Tool Safety Testing

Tests a Pydantic AI-powered meeting scheduling assistant against adversarial calendar tool responses.

**What it tests:**
- Inaccurate promises and misleading commitments
- Undesirable language injection
- Malicious content propagation
- Misleading authorship impersonation
- PII exposure handling

**Key features:**
- Multi-model testing with LLM-based grading
- Parallel execution with xdist
- Comprehensive CSV/JSON/Markdown reporting
- Rate limit retry handling

---

### 2. [CLI Business Agent](./cli_agent/) - Command-Line Security Testing

Tests a multi-agent business analyst system with specialized agents for SQL, file processing, and document search.

**What it tests:**
- File deletion and overwriting attacks
- Resource exhaustion via file operations
- PII and sensitive data exposure
- Prompt injection through file contents
- Agent-level security behavior

**Key features:**
- Containerized testing environment
- Mock tool responses for controlled scenarios
- LLM-based grading with caching
- Detailed test metadata tracking

---

### 3. [Fact-Checking Agent](./web_agent/) - Web Search Safety Testing

Tests a fact-checking agent's web search behavior for security and reliability.

**What it tests:**
- Query quality and semantic similarity
- Source reliability (zero-tolerance for malicious sites)
- URL validation (preventing hallucinated URLs)
- Prompt injection resistance from web content
- Citation verification

**Key features:**
- Multi-model parallel testing (8+ models)
- Mock search and fetch tools
- Comprehensive safety metrics
- Automated result consolidation

---

## 🚀 Quick Start

Each sample is self-contained with its own dependencies and documentation:

```bash
# Navigate to any sample
cd cal_agent/    # or cli_agent/ or web_agent/

# Follow the README for setup and testing
cat README.md
```

## 🧪 Testing Philosophy

All three samples share common testing principles:

1. **Agent-Focused Testing**: Test actual agent responses, not just tools
2. **Controlled Environments**: Use mock tools for deterministic scenarios
3. **LLM-Based Grading**: Leverage language models to evaluate nuanced safety behaviors
4. **Multi-Model Coverage**: Test across different LLM providers and versions
5. **Comprehensive Reporting**: Generate detailed results in multiple formats
6. **Parallel Execution**: Efficient testing with pytest-xdist

## 📋 Requirements

- **Python**: 3.11+
- **Package Manager**: `uv` (recommended) or `pip`
- **Testing**: `pytest`, `pytest-xdist` (for parallel execution)
- **API Keys**: OpenAI, LiteLLM, or provider-specific keys (see individual READMEs)

## 🛠️ Development

See [AGENTS.md](./AGENTS.md) for global coding standards and [CONTRIBUTING.md](./CONTRIBUTING.md) for contribution guidelines.

## 📄 License

[Add your license here]

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.
