"""Adapter protocol shared by every target."""

from __future__ import annotations

from typing import Any, Protocol

from ..models import AgentResponse, ToolCall

__all__ = ["AgentResponse", "TargetAdapter", "ToolCall"]


class TargetAdapter(Protocol):
    """A target agent Redline can drive.

    Implementations must be deterministic enough to test and must never expose
    a shell-execution tool.
    """

    name: str

    def send(self, prompt: str, context: dict[str, Any] | None = None) -> AgentResponse:
        ...

    def snapshot(self) -> dict[str, Any]:
        """Observable state used by the state validator."""

    def platform_marker(self) -> str | None:
        """Authoritative platform signal, if the target exposes one."""
