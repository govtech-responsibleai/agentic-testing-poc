# Agent Testing Environment Guide

In this repository, we are testing a CLI agent that assists a business analyst, accessing financial data from a SQLite database and other documents.

## Build & Run Commands
- **Setup API key**: `cp .env.example .env` then edit .env with your OpenAI API key
- **Build container**: `podman build -t business-sim .`
- **Run interactive agents**: `podman run -it --env-file .env business-sim`
- **Run agents interactively**: `podman run -it --env-file .env --entrypoint python business-sim -m src.business_agents`
- **Run single query**: Call `main(input="your query", interactive=False)` for programmatic use
- **Alternative**: `podman run -it -e OPENAI_API_KEY=sk-your-key business-sim`
- **Generate test data**: `python src/data_generation.py` (run locally or in container)
- **Test database**: `sqlite3 src/business.sqlite ".tables"`

## Testing & Safety
- **Install test dependencies**: `pip install pytest pytest-asyncio`
- **Run safety tests**: `pytest tests/test_cli_agent.py -v` 
- **Run specific test category**: `pytest tests/test_cli_agent.py::TestFileAgentSafety::test_destructive_commands_blocked -v`
- **Quick status check**: `pytest tests/test_cli_agent.py --tb=no -q`
- **Safety test coverage**: 25 tests across 5 security risk categories
  - File deletion/overwriting attacks (3 tests)
  - Resource exhaustion via file operations (3 tests)  
  - PII/sensitive data exposure from files (3 tests)
  - Prompt injection attacks via file contents (3 tests)
  - Agent-level security testing (3 tests)

### Test Status
- **✅ Infrastructure Working**: 20/25 tests passing (fixtures, API calls, test framework)
- **⚠️ Security Issues Found**: 5/25 tests failing (real vulnerabilities identified)
- **Test files**: `tests/test_cli_agent.py`, `tests/fixtures/test_cases.py`, `tests/conftest.py`

## Architecture
- **Multi-agent system** (`src/business_agents.py`) - OpenAI Agents SDK with handoffs between SQL Analyst, File Processor, Meeting Minutes Searcher, and Report Writer
- **SQLite database** (`src/business.sqlite`) - Products, customers, orders, order_details tables
- **Sample data** (`src/docs/`) - Generated PDFs (invoices/receipts), CSV files, and 50 meeting minutes
- **Vector database** (`src/chroma_db/`) - Semantic search over meeting minutes using ChromaDB
- **Data generation** (`src/data_generation.py`) - Creates realistic business data using Faker
- **Pre-cached models** (`models/`) - Embedding models cached locally for faster builds

## Agent System
- **Business Analyst Coordinator** - Main agent that delegates to specialists
- **SQL Analyst** - Database queries and structured data analysis  
- **File Processor** - Command-line file analysis (ls, cat, grep, head, tail, etc.)
- **Meeting Minutes Searcher** - Vector search through 50+ meeting minutes
- **Report Writer** - Generate formatted business reports in Markdown

## File Structure
```
/app/src/                    # Source code (container)
├── business_agents.py       # Main multi-agent system
├── data_generation.py       # Generate all sample data
├── db.py                   # Database helper functions
├── vector_db.py            # ChromaDB vector search utilities
├── download_model.py       # Pre-download embedding models
├── business.sqlite         # SQLite database (generated)
├── chroma_db/              # Vector database (generated)
└── docs/                   # Sample data (generated)
    ├── pdf/                # Invoice and receipt PDFs
    ├── csv/                # Business data CSVs
    └── meeting_minutes/    # 50 realistic meeting minutes

/app/reports/               # Agent-generated reports (writable)
/root/.cache/chroma/        # Pre-cached embedding models
models/                     # Local model cache (copied to container)
```

## Database Schema
```sql
-- Products table
CREATE TABLE products (sku, name, category, price, stock);

-- Customers table  
CREATE TABLE customers (customer_id, name, contact_name, email, phone, address);

-- Orders table
CREATE TABLE orders (order_id, customer_id, order_date, status);

-- Order details table
CREATE TABLE order_details (order_id, sku, quantity, unit_price, total);
```

## Sample Data Details
- **50 products** across 4 categories (Office Supplies, Electronics, Furniture, Stationery)
- **25 business customers** with realistic company names and contacts
- **150 orders** with 1-5 items each, realistic dates and statuses
- **15 invoice PDFs** with structured business information
- **10 expense receipt PDFs** for various business expenses
- **50 meeting minutes** from 7 meeting types (Sales, Finance, HR, Operations, Product, Marketing, Board)

## Agent Tools & Capabilities
### SQL Analyst Tools:
- `query_database(query: str)` - Execute SQL queries against SQLite database
- Returns structured JSON with query results and metadata

### File Processor Tools:
- `run_command(command: str)` - Execute safe shell commands (ls, cat, head, tail, grep, wc, find, du, file)
- `list_available_files()` - List all PDFs, CSVs, and meeting minutes
- Working directory: `/app/src/docs`

### Meeting Minutes Searcher Tools:
- `search_meeting_minutes(query: str, n_results: int)` - Vector similarity search
- Returns relevant meeting excerpts with metadata (type, date, filename)

### Report Writer Tools:
- `write_report(title: str, content: str, format: str)` - Generate Markdown reports
- Saves to `/app/reports/` directory

## Environment Variables
- `OPENAI_API_KEY` - Required for OpenAI Agents SDK
- `PYTHONPATH=/app/src` - Set in container for module imports

## Development Workflow
1. **Local development**: Run `python src/business_agents.py` directly
2. **Data regeneration**: Delete `src/business.sqlite` and run `python src/data_generation.py`
3. **Container testing**: Build with `podman build -t business-sim .`
4. **Interactive testing**: Use OpenAI Agents SDK's `run_demo_loop` for conversation flow
5. **Non-interactive mode**: Call `main(input="your query", interactive=False)` to run single queries
6. **Agent modifications**: Edit tools in `src/business_agents.py`, rebuild container

## Common Use Cases
- **Database analysis**: "What are our top selling products?" → SQL Analyst
- **File exploration**: "List all invoice files" → File Processor  
- **Historical context**: "Find meetings about budget planning" → Meeting Minutes Searcher
- **Report generation**: "Create a Q1 sales summary" → Report Writer + coordination
- **Multi-step analysis**: Combines multiple agents for complex business questions

## Troubleshooting
- **"OPENAI_API_KEY not set"**: Ensure `.env` file exists with valid API key
- **"Vector database not found"**: Run data generation or rebuild container  
- **"Command not allowed"**: File Processor only allows safe commands (ls, cat, grep, etc.)
- **Agent not responding**: Check API key validity and internet connection
- **Build failures**: Run `podman system prune -a -f` to free disk space

## Code Style  
- Use **pathlib.Path** for file operations, **asyncio** for agents, **Pydantic** for data models
- Database queries return **sqlite3.Row** objects, convert to dicts for JSON serialization
- Import order: standard library, third-party, local modules
- Use **typing hints**, **docstrings** for functions, handle exceptions with try/except
- File paths: `/app/src/` (container), `/app/reports/` (output), tools use absolute paths
- Agent tools return JSON strings for structured data, plain text for simple responses
- Error handling: Return descriptive error messages, don't raise exceptions in tools
