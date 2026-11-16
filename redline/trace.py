"""Replay a locally captured trace through the standard validators."""

import json
from copy import deepcopy
from pathlib import Path

from .models import AgentResponse, ToolCall

PHASES = ("initial", "before_attack", "after_attack")


class TraceAdapter:
    """Read-only adapter: no prompts are sent, no state is modified."""

    name = "trace"

    def __init__(self, data: dict) -> None:
        try:
            self.target = data["target"]
            prompts = (data["baseline_prompt"], data["attack_prompt"])
            responses = (data["baseline"], data["attack"])
            snapshots = [data["snapshots"][phase] for phase in PHASES]
            markers = [data["markers"][phase] for phase in PHASES]
            for response in responses:
                if (not isinstance(response, dict)
                        or not isinstance(response.get("text"), str)
                        or not isinstance(response.get("tool_calls"), list)):
                    raise ValueError("trace response needs text and tool_calls")
                for call in response["tool_calls"]:
                    if (not isinstance(call, dict) or not isinstance(call.get("name"), str)
                            or not isinstance(call.get("arguments", {}), dict)):
                        raise ValueError("trace tool call needs name and object arguments")
            if any(not isinstance(snapshot, dict) for snapshot in snapshots):
                raise ValueError("trace snapshots must be objects")
            if any(not isinstance(prompt, str) for prompt in prompts):
                raise ValueError("trace prompts must be strings")
            if not isinstance(self.target, str) or not self.target:
                raise ValueError("trace target must be a nonempty string")
            json.dumps(data, allow_nan=False)
        except (KeyError, TypeError, IndexError) as exc:
            raise ValueError(f"invalid trace: {exc}") from exc
        self._prompts = prompts
        self._responses = [
            AgentResponse(
                response["text"],
                [ToolCall(call["name"], call.get("arguments", {})) for call in response["tool_calls"]],
            )
            for response in responses
        ]
        self._snapshots = snapshots
        self._markers = markers
        self._sent = 0
        self._snap = 0
        self._marker = 0

    @classmethod
    def from_file(cls, path) -> "TraceAdapter":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @staticmethod
    def _next(index: int, values: list, label: str):
        if index >= len(values):
            raise ValueError(f"trace has no remaining {label}")
        return values[index]

    def send(self, prompt: str) -> AgentResponse:
        if self._sent >= len(self._responses):
            raise ValueError("trace has no remaining responses")
        if prompt != self._prompts[self._sent]:
            raise ValueError("trace prompt does not match the scenario prompt")
        response = self._responses[self._sent]
        self._sent += 1
        return response

    def snapshot(self) -> dict:
        value = deepcopy(self._next(self._snap, self._snapshots, "snapshots"))
        self._snap += 1
        return value

    def platform_marker(self):
        value = self._next(self._marker, self._markers, "markers")
        self._marker += 1
        return value
