"""Shared data types (no logic, no imports from other redline modules)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCall:
    """One tool invocation requested by the agent."""

    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """What the target returned for one prompt."""

    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class ValidatorResult:
    """Outcome of one independent validator."""

    name: str
    outcome: str  # Confirmed | Blocked | Not observed
    detail: str
