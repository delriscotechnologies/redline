"""Target adapters: the surface Redline talks to."""

from .base import AgentResponse, TargetAdapter, ToolCall
from .mock import InjectionRule, MockAdapter, MockWorld

__all__ = [
    "AgentResponse",
    "InjectionRule",
    "MockAdapter",
    "MockWorld",
    "TargetAdapter",
    "ToolCall",
]
