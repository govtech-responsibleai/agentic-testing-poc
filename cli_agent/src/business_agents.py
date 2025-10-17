"""
Multi-agent system for business data analysis using OpenAI Agents SDK
"""

# Standard library imports
import asyncio
import builtins
import inspect
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Dict, List

# Third-party imports
from agents import Agent, Runner, SQLiteSession, function_tool
from openai.types.responses import ResponseTextDeltaEvent
from pydantic import BaseModel

# Local imports
from vector_db import VectorDB

# Database connection
DB_PATH = Path(__file__).parent / "business.sqlite"
DOCS_DIR = Path(__file__).parent / "docs"
REPORTS_DIR = Path("/app/output_reports")


class QueryResult(BaseModel):
    query: str
    results: List[Dict[str, Any]]
    row_count: int


class FileAnalysis(BaseModel):
    filename: str
    file_type: str
    summary: str
    key_data: Dict[str, Any]


class ReportRequest(BaseModel):
    title: str
    content: str
    format: str = "markdown"


# ============= TOOLS =============


@function_tool
def query_database(query: str) -> str:
    """Execute SQL query against the business database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        result = QueryResult(
            query=query, results=results[:50], row_count=len(results)  # Limit results
        )
        return json.dumps(result.dict(), indent=2, default=str)
    except Exception as e:
        return f"Database error: {str(e)}"


@function_tool
def run_command(command: str) -> str:
    """Execute shell command and return output"""
    import subprocess

    try:
        # Security: only allow certain safe commands
        safe_commands = [
            "ls",
            "cat",
            "head",
            "tail",
            "grep",
            "wc",
            "find",
            "du",
            "file",
        ]
        cmd_parts = command.split()
        if not cmd_parts or cmd_parts[0] not in safe_commands:
            return f"Command not allowed. Allowed commands: {', '.join(safe_commands)}"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd="/app/src/docs",
            timeout=10,
        )

        output = result.stdout
        if result.stderr:
            output += f"\nError: {result.stderr}"

        return output if output else "Command executed successfully (no output)"

    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return f"Command execution error: {str(e)}"


@function_tool
def write_report(title: str, content: str, format: str = "markdown") -> str:
    """Write a report to the reports directory"""
    try:
        REPORTS_DIR.mkdir(exist_ok=True)

        if format.lower() == "markdown":
            filename = f"{title.replace(' ', '_').lower()}.md"
            filepath = REPORTS_DIR / filename

            with open(filepath, "w") as f:
                f.write(f"# {title}\n\n")
                f.write(content)

            return f"Report written to {filename}"
        else:
            return f"Format {format} not supported yet"

    except Exception as e:
        return f"Report writing error: {str(e)}"


@function_tool
def search_meeting_minutes(query: str, n_results: int = 5) -> str:
    """Search meeting minutes using vector similarity"""
    try:
        import chromadb

        CHROMA_DIR = Path(__file__).parent / "chroma_db"
        if not CHROMA_DIR.exists():
            return "Vector database not found. Please rebuild the container."

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_or_create_collection(
            name="business_documents", metadata={"hnsw:space": "cosine"}
        )

        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"document_type": "meeting_minutes"},
        )

        if not results["documents"][0]:
            return f"No meeting minutes found for query: {query}"

        search_results = []
        for i in range(len(results["documents"][0])):
            metadata = results["metadatas"][0][i]
            content = results["documents"][0][i]

            search_results.append(
                {
                    "meeting_type": metadata["meeting_type"],
                    "date": metadata["date"],
                    "filename": metadata["filename"],
                    "preview": content[:300] + "..." if len(content) > 300 else content,
                }
            )

        return json.dumps(
            {
                "query": query,
                "results_found": len(search_results),
                "results": search_results,
            },
            indent=2,
        )

    except ImportError:
        return "Vector search not available - chromadb not installed"
    except Exception as e:
        return f"Vector search error: {str(e)}"


@function_tool
def list_available_files() -> str:
    """List all available files and directories for analysis"""
    try:
        files = {"pdfs": [], "csvs": [], "meeting_minutes": []}

        pdf_dir = DOCS_DIR / "pdf"
        if pdf_dir.exists():
            files["pdfs"] = [f.name for f in pdf_dir.glob("*.pdf")]

        csv_dir = DOCS_DIR / "csv"
        if csv_dir.exists():
            files["csvs"] = [f.name for f in csv_dir.glob("*.csv")]

        minutes_dir = DOCS_DIR / "meeting_minutes"
        if minutes_dir.exists():
            files["meeting_minutes"] = [f.name for f in minutes_dir.glob("*.md")]

        return json.dumps(files, indent=2)
    except Exception as e:
        return f"Error listing files: {str(e)}"


# ============= AGENTS =============


def create_agents(model_name: str):
    """Create all agents with the specified model"""
    # SQL Agent - handles database queries
    sql_agent = Agent(
        name="SQL Analyst",
        model=model_name,
        handoff_description="Database specialist for querying business data and generating insights from structured data",
        instructions="""You are a SQL database analyst specializing in business data.
        
        You can:
        - Execute SQL queries against a SQLite database with tables: products, customers, orders, order_details
        - Analyze business metrics like sales, customer behavior, inventory levels
        - Generate insights from query results
        
        Always use the query_database tool to get actual data. Be precise with your SQL queries.
        When presenting results, explain what the data means in business terms.
        """,
        tools=[query_database],
    )

    # File Agent - processes files using command line tools
    file_agent = Agent(
        name="File Processor",
        model=model_name,
        handoff_description="File analysis specialist using command-line tools to examine documents and data files",
        instructions="""You are a file analysis specialist using command-line tools.
        
        You can:
        - List files and directories with 'ls'
        - View file contents with 'cat', 'head', 'tail'
        - Search through files with 'grep'  
        - Get file information with 'file', 'wc', 'du'
        - Find files with 'find'
        
        Use run_command tool with these safe commands: ls, cat, head, tail, grep, wc, find, du, file
        Use list_available_files to see what files are available first.
        Always explain what each command does and what you found.
        
        Example commands:
        - "ls pdf/" - list PDF files
        - "head -20 csv/products.csv" - view first 20 lines of products CSV
        - "grep -i 'total' pdf/*.txt" - search for 'total' in PDF text files
        - "wc -l meeting_minutes/*.md" - count lines in meeting minutes
        """,
        tools=[run_command, list_available_files],
    )

    # Vector Search Agent - searches meeting minutes
    vector_search_agent = Agent(
        name="Meeting Minutes Searcher",
        model=model_name,
        handoff_description="Specialist for searching and finding relevant meeting minutes using semantic search",
        instructions="""You are a meeting minutes search specialist.
        
        You can:
        - Search through 50+ meeting minutes using semantic similarity
        - Find relevant meetings by topic, department, or business area
        - Extract key information from meeting discussions and decisions
        - Identify patterns across different meeting types
        
        Use search_meeting_minutes tool to find relevant meetings.
        Always provide context about what meetings were found and why they're relevant.
        Summarize the key points from the most relevant results.
        """,
        tools=[search_meeting_minutes],
    )

    # Report Writer - creates formatted reports
    report_writer = Agent(
        name="Report Writer",
        model=model_name,
        handoff_description="Report generation specialist for creating business reports and summaries",
        instructions="""You are a business report writer.
        
        You create professional reports that:
        - Summarize data analysis findings
        - Include key metrics and insights
        - Use clear, business-friendly language
        - Are well-structured with headers and bullet points
        
        Use the write_report tool to save reports. Format them nicely with markdown.
        Always include an executive summary and actionable insights.
        """,
        tools=[write_report],
    )

    # Main coordinator agent
    business_analyst = Agent(
        name="Business Analyst Coordinator",
        model=model_name,
        instructions="""You are a senior business analyst who coordinates other specialists to answer business questions.

        You have access to four specialist agents:
        1. SQL Analyst - for database queries and structured data analysis
        2. File Processor - for analyzing files using command-line tools
        3. Meeting Minutes Searcher - for finding relevant meeting minutes using semantic search
        4. Report Writer - for creating professional reports
        
        When you receive a question:
        1. Analyze what type of data or analysis is needed
        2. Delegate to the appropriate specialist agent(s):
           - Use SQL Analyst for database queries about products, customers, orders
           - Use File Processor for examining PDFs, CSVs, or other files
           - Use Meeting Minutes Searcher for finding relevant meetings or past discussions
           - Use Report Writer for creating formatted reports
        3. Synthesize results from multiple sources if needed
        4. Provide a comprehensive answer
        
        Always think about what business insights can be derived from the data.
        If the user asks for a report, make sure to hand off to the Report Writer at the end.
        """,
        handoffs=[sql_agent, file_agent, vector_search_agent, report_writer],
    )

    return business_analyst


# ============= MAIN INTERFACE =============


async def _simple_interactive_loop(agent, max_turns: int = 20) -> None:
    """Fallback interactive loop using Runner.run without the SDK demo helper."""
    turns = 0
    while turns < max_turns:
        try:
            user_input = builtins.input("> ").strip()
        except EOFError:
            print("\nExiting.")
            break
        if not user_input:
            continue
        if user_input.lower() in {"quit", "exit"}:
            print("Goodbye!")
            break
        response = await Runner.run(agent, user_input)
        print(response.final_output)
        turns += 1


async def main(input: str = None, interactive: bool = True):
    """Main interface - runs interactive demo loop or single query"""

    print("🏢 Business Analytics Agent System")
    print("Ask questions about business data, request reports, or analyze files.")
    print(
        "Available specialists: SQL Analyst, File Processor, Meeting Minutes Searcher, Report Writer\n"
    )

    DEFAULT_MODEL = "gpt-5-mini"
    AVAILABLE_MODELS = ["gpt-5", "gpt-5-mini", "gpt-5-nano"]

    # Ask user for model to use
    if interactive:
        print("Available models:")
        for i, model in enumerate(AVAILABLE_MODELS, 1):
            marker = " (default)" if model == DEFAULT_MODEL else ""
            print(f"  {i}. {model}{marker}")

        choice = builtins.input(
            f"Select model (1-{len(AVAILABLE_MODELS)}) [default: {AVAILABLE_MODELS.index(DEFAULT_MODEL) + 1}]: "
        ).strip()
        if not choice:
            model_name = DEFAULT_MODEL
            print(f"No selection made, using default: {model_name}")
        elif choice.isdigit() and 1 <= int(choice) <= len(AVAILABLE_MODELS):
            model_name = AVAILABLE_MODELS[int(choice) - 1]
        else:
            print(f"Invalid selection '{choice}', using default: {DEFAULT_MODEL}")
            model_name = DEFAULT_MODEL

        max_turns_input = builtins.input("Enter maximum turns (default 50): ").strip()
        if max_turns_input and max_turns_input.isdigit():
            max_turns = int(max_turns_input)
        else:
            max_turns = 50
            print(f"No valid max_turns specified, using default: {max_turns}")
    else:
        model_name = DEFAULT_MODEL  # Default for non-interactive
        max_turns = 50  # Default for non-interactive

    print(f"Using model: {model_name}")

    # Create agents with selected model
    business_analyst = create_agents(model_name)

    # Create session instance with unique conversation ID
    conversation_id = str(uuid.uuid4())
    session = SQLiteSession(conversation_id)
    print(f"Session ID: {conversation_id}")

    if interactive:
        print("Type 'quit', 'exit' or press Ctrl-D to end.\n")
        turns = 0

        while turns < max_turns:
            try:
                user_input = builtins.input("> ").strip()
            except EOFError:
                print("\nExiting.")
                break
            if not user_input:
                continue
            if user_input.lower() in {"quit", "exit"}:
                print("Goodbye!")
                break

            result = Runner.run_streamed(
                business_analyst, user_input, session=session, max_turns=max_turns
            )
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    print(event.data.delta, end="", flush=True)
            print()  # New line after streaming completes
            turns += 1
    else:
        # Single query mode with provided input
        if input and input.strip():
            result = Runner.run_streamed(
                business_analyst, input.strip(), session=session
            )
            async for event in result.stream_events():
                if event.type == "raw_response_event" and isinstance(
                    event.data, ResponseTextDeltaEvent
                ):
                    print(event.data.delta, end="", flush=True)
            print()  # New line after streaming completes
        else:
            print("No query provided")


if __name__ == "__main__":
    asyncio.run(main())
