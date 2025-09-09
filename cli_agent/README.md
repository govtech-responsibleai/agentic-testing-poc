# Testing CLI Agent

A testing environment for CLI agents, part of the **Agentic Testing POC** mono-repository. This environment provides simplified simulation where the CLI agent assists a business analyst, accessing financial data from a SQLite database and other documents.

## What's Inside

- **Multi-Agent System**: OpenAI Agents SDK with specialized business analysts
- **SQLite Database**: Products, customers, orders, and order details
- **Sample PDFs**: Invoices and expense receipts 
- **CSV Files**: Structured business data
- **Meeting Minutes**: 50 realistic meeting minutes with vector search
- **Vector Database**: ChromaDB for semantic search over documents
- **Pre-cached Models**: Embedding models for faster builds

## Quick Start

```bash
# 1. Set up your OpenAI API key
cp .env.example .env
# Edit .env and add your OpenAI API key

# 2. Build the container
podman build -t business-sim .

# 3. Run the interactive agent system
podman run -it --env-file .env business-sim

# Or run with bash access
podman run -it --env-file .env --entrypoint bash business-sim
```

### Alternative: Pass API key directly
```bash
podman run -it -e OPENAI_API_KEY=sk-your-key-here business-sim
```

## Agent System

The simulation includes four specialized agents:

- **Business Analyst Coordinator** - Main orchestrator that delegates tasks
- **SQL Analyst** - Database queries and structured data analysis  
- **File Processor** - Command-line file analysis (ls, cat, grep, head, tail, etc.)
- **Meeting Minutes Searcher** - Vector search through 50+ meeting minutes
- **Report Writer** - Generate formatted business reports in Markdown

## How It Works

The interactive system allows you to:

1. **Ask business questions** - The coordinator routes to appropriate specialists
2. **Query databases** - SQL Analyst handles complex database queries
3. **Analyze files** - File Processor uses command-line tools to examine documents
4. **Search meetings** - Vector search finds relevant meeting discussions
5. **Generate reports** - Report Writer creates professional Markdown reports

### Example Interactions

```
> What are our top selling products this quarter?
[Hands off to SQL Analyst for database query]

> Search for meetings about budget planning
[Hands off to Meeting Minutes Searcher for vector search]

> Analyze the invoice PDFs in the system
[Hands off to File Processor for document analysis]

> Create a sales performance report
[Coordinates multiple agents, then hands off to Report Writer]
```

## File Locations

- SQLite database: `/app/src/business.sqlite`
- PDF files: `/app/src/docs/pdf/`
- CSV files: `/app/src/docs/csv/`
- Meeting minutes: `/app/src/docs/meeting_minutes/`
- Vector database: `/app/src/chroma_db/`
- Reports output: `/app/reports/`

## Sample Data

The simulation includes:
- 50 products across 4 categories
- 25 business customers
- 150 orders with details
- 15 invoice PDFs
- 10 expense receipt PDFs
- 50 meeting minutes from various departments (Sales, Finance, HR, Operations, etc.)

All data is generated with realistic business scenarios using the Faker library and includes semantic relationships for meaningful agent interactions.

## Relation to Web Agent Testing

This environment is part of the broader **Agentic Testing POC** that includes:

- **`web_agent`**: Safety testing framework for fact-checking agents that use web search
- **`cli_agent`**: This environment - business simulation and agent testing infrastructure

### Supporting Web Agent Safety Tests

While this environment focuses on business data simulation, it provides the foundation for testing web-based agents by offering:

1. **Controlled Data Environment**: Realistic business scenarios for testing agent reasoning
2. **Multi-Agent Architecture**: Framework for testing complex agent interactions  
3. **Vector Search Capabilities**: Semantic search testing over document collections
4. **Report Generation**: Structured output testing and validation
5. **Containerized Testing**: Isolated, reproducible test environments

### Integration with Web Agent Testing

The `web_agent` project tests fact-checking agents across 5 critical safety metrics:
- **Query Quality**: Search query appropriateness
- **Source Reliability**: Avoiding malicious/unreliable sources  
- **URL Validation**: Preventing hallucinated URLs
- **Prompt Injection Resistance**: Resilience against web-based attacks
- **Citation Verification**: Accurate source attribution

This `cli_agent` environment can be extended to support similar safety testing by providing:
- **Mock web services** for controlled testing
- **Business context data** for realistic fact-checking scenarios  
- **Multi-model testing infrastructure** similar to the web agent framework
- **Comprehensive logging and reporting** for safety metric evaluation

## Future Enhancements

Planned extensions to support web agent safety testing:
- Mock web search APIs with controlled results
- Prompt injection testing capabilities
- URL validation and source classification
- Integration with the web agent testing framework
- Cross-environment test result aggregation
