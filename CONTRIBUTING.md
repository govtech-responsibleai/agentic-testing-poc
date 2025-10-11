# Contributing to Agentic Testing Samples

Thank you for your interest in contributing! This document provides guidelines for contributing to the agentic testing samples.

## 🚀 Getting Started

1. **Fork the repository** and clone your fork
2. **Create a branch** for your changes: `git checkout -b feat/your-feature-name`
3. **Make your changes** following the coding standards below
4. **Test your changes** thoroughly
5. **Submit a pull request** with a clear description

## 📝 Coding Standards

All code must follow the standards defined in [AGENTS.md](./AGENTS.md):

- **Python Version**: 3.11+
- **Type Hints**: Required for all functions and methods
- **Code Style**: PEP 8 conventions
- **Imports**: Sorted alphabetically (standard library, third-party, local)
- **Docstrings**: Required for public modules, classes, and functions
- **String Formatting**: Prefer f-strings
- **Logging**: Use the `logging` module instead of `print`

## 🧪 Testing Requirements

- **Unit Tests**: Write tests for new functionality using pytest
- **Test Coverage**: Ensure new code is adequately tested
- **Existing Tests**: All existing tests must pass
- **Test Documentation**: Update test documentation when adding new test scenarios

## 📋 Pull Request Guidelines

### PR Title Format

Follow this pattern: `<type>: <short summary>`

Types:
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `chore` - Maintenance tasks
- `refactor` - Code refactoring
- `test` - Test additions or modifications

Examples:
- `feat: add rate limit retry to web_agent tests`
- `fix: handle missing API keys gracefully`
- `docs: update cal_agent README with setup instructions`

### PR Description

Include:
- **What**: Summary of changes
- **Why**: Motivation and context
- **How**: Implementation approach (if non-obvious)
- **Testing**: How you tested the changes
- **Breaking Changes**: Note any breaking changes

## 📂 Repository Structure

Each sample is self-contained:

```
sample_name/
├── README.md          # Sample-specific documentation
├── AGENTS.md          # Development guidance
├── TESTING.md         # Testing documentation
├── src/               # Source code
├── tests/             # Test suite
│   ├── agentic_testing/  # Safety test framework
│   ├── test_*.py      # Test files
│   └── conftest.py    # Pytest configuration
└── [dependency files] # pyproject.toml, requirements.txt, etc.
```

## 🐛 Reporting Issues

When reporting issues, please include:

- **Description**: Clear description of the issue
- **Reproduction Steps**: How to reproduce the problem
- **Expected Behavior**: What you expected to happen
- **Actual Behavior**: What actually happened
- **Environment**: Python version, OS, relevant package versions
- **Logs**: Relevant log output or error messages

## 💡 Suggesting Features

Feature suggestions are welcome! Please:

- **Search existing issues** to avoid duplicates
- **Describe the use case** clearly
- **Explain the benefit** to other users
- **Consider implementation** if you can

## 🔍 Code Review Process

1. All PRs require review before merging
2. Address review feedback promptly
3. Keep PRs focused and reasonably sized
4. Update documentation for user-facing changes
5. Ensure CI checks pass

## 🤝 Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the code of conduct

## 📞 Questions?

- Open an issue for questions about contributing
- Tag issues with `question` for clarification requests
- Be patient - maintainers are often volunteers

Thank you for contributing! 🎉
