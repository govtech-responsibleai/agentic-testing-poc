# AGENTS.md

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
