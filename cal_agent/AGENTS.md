# Global Guidance

This file provides global guidance for contributors working in this repository. These rules apply unless a more specific `AGENTS.md` overrides them.

## Python Version
- Use **Python 3.11**.

## Code Style
- Include **type hints** for all functions and methods.
- Follow **PEP8** conventions.
- Sort imports **alphabetically** within their respective groups (standard library, third-party, local).

## Documentation
- Provide descriptive **docstrings** for public modules, classes, and functions.

## Testing
- Write unit tests for new functionality using **pytest**.

## Best Practices
- Prefer **f-strings** for string formatting.
- Use the **logging** module instead of `print` for runtime information.

## Pull Requests
- PR titles must follow the pattern `<type>: <short summary>` where `type` is one of `feat`, `fix`, `docs`, `chore`, `refactor`, or `test`.
- Keep titles concise and descriptive.

# Repository Guidance

This document supplements the global contributor instructions. Follow these project-specific rules when working on the meeting scheduler agent.

## Environment & Tooling
- Target **Python 3.11** exclusively.
- Keep dependencies minimal and document any additions in `README.md`.
- Store secrets (e.g., `OPENAI_API_KEY`) in `.env`; never hard-code credentials.

## Code Style
- Adhere to **PEP 8** and include **type hints** on all functions, methods, and data classes.
- Sort imports alphabetically within standard library, third-party, and local groups.
- Prefer **f-strings** for string formatting and use the **logging** module for runtime output.

## Documentation
- Provide docstrings for public modules, classes, and functions.
- Update `README.md` whenever the CLI interface or configuration expectations change.

## Testing
- Write and run **pytest** unit tests for all new behaviour.
- Ensure tests run deterministically; seed or mock randomness as needed.
- Use the existing `tests/` layout for new cases (e.g., mirror module structure).

## Logging & CLI
- The CLI must remain interactive (no one-shot invocations). Preserve the JSON response after each request.
- All logging should route through the configured file handler; avoid printing logs to stdout/stderr.

## Workflow
- Before submitting changes: format, lint (if tooling is available), and execute `pytest`.
- Do not alter artefacts outside `src/`, `tests/`, documentation, or configuration without prior discussion.

These rules extend the global guidance above. If conflicts arise, the more specific guidance in this section takes precedence.
