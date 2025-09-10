from __future__ import annotations

"""Minimal local Agents SDK stub for tests.

This lightweight module exposes the minimal surface area used by the
project's tests and business_agents module. It intentionally avoids any
network calls to keep the test environment self-contained.
"""
from dataclasses import dataclass, field
from typing import Any, Callable, List


def function_tool(fn: Callable) -> Callable:
    """Decorator used in tests – returns the function unchanged."""
    return fn


@dataclass
class Agent:
    name: str
    model: str
    instructions: str = ""
    tools: List[Callable] = field(default_factory=list)
    handoffs: List["Agent"] = field(default_factory=list)
    handoff_description: str = ""


class _Response:
    def __init__(self, final_output: str):
        self.final_output = final_output


class Runner:
    """Simple runner that invokes the first tool of the agent."""

    @staticmethod
    async def run(agent: Agent, prompt: str, **_: Any) -> _Response:
        if agent.tools:
            # Call the first tool with the raw prompt; tests patch the tool
            # to return predetermined strings, so argument content is
            # irrelevant for assertions.
            output = agent.tools[0](prompt)
        else:
            output = ""
        return _Response(output)


async def run_demo_loop(agent: Agent, max_turns: int = 20) -> None:  # pragma: no cover
    """Stubbed interactive loop – no-op for testing."""
    return None
