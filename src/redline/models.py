from dataclasses import dataclass, field
from typing import Any, Protocol

MOCK_TARGET = "mock://invoice-agent"


@dataclass
class ToolCall:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)


@dataclass
class ValidatorResult:
    name: str
    outcome: str
    detail: str


class TargetAdapter(Protocol):
    name: str
    target: str

    def send(self, prompt: str) -> AgentResponse: ...
    def snapshot(self) -> dict[str, Any]: ...
    def platform_marker(self) -> str | None: ...
