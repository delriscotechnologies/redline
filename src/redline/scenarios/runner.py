"""Execute a declared scenario and capture the evidence."""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from ..adapters.base import TargetAdapter
from ..config import Scope
from ..evidence.ledger import append_record
from ..models import ValidatorResult
from ..validators import run_validators


@dataclass
class Scenario:
    id: str
    technique_id: str
    adapter: str
    target: str
    baseline_prompt: str
    attack_prompt: str
    expect: dict[str, Any] = field(default_factory=dict)
    validators: list[str] = field(
        default_factory=lambda: ["tool_trace", "state", "platform"]
    )


@dataclass
class RunResult:
    run_id: str
    scenario_id: str
    technique_id: str
    target: str
    mode: str
    status: str
    baseline: dict[str, Any]
    attack: dict[str, Any]
    state_before: dict[str, Any]
    state_after: dict[str, Any]
    validators: list[ValidatorResult]
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_scenario(path: str | Path) -> Scenario:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return Scenario(**data)


def _aggregate(validator_results: list[ValidatorResult]) -> str:
    if any(v.outcome == "Confirmed" for v in validator_results):
        return "Confirmed"
    if validator_results and all(v.outcome == "Blocked" for v in validator_results):
        return "Blocked"
    return "No breach observed"


def run_scenario(
    scenario: Scenario,
    adapter: TargetAdapter,
    scope: Scope,
    *,
    mode: str = "vulnerable",
    ledger_path: str | Path | None = None,
) -> RunResult:
    state_before = adapter.snapshot()

    baseline_response = adapter.send(scenario.baseline_prompt)
    attack_response = adapter.send(scenario.attack_prompt)
    if adapter.requests > scope.max_requests:
        raise RuntimeError(
            f"request limit exceeded: {adapter.requests} > {scope.max_requests}"
        )

    state_after = adapter.snapshot()
    marker = adapter.platform_marker()

    validator_results = run_validators(
        scenario,
        attack=attack_response,
        state_before=state_before,
        state_after=state_after,
        marker=marker,
    )

    run_id = uuid.uuid4().hex[:12]
    result = RunResult(
        run_id=run_id,
        scenario_id=scenario.id,
        technique_id=scenario.technique_id,
        target=scenario.target,
        mode=mode,
        status=_aggregate(validator_results),
        baseline={
            "prompt": scenario.baseline_prompt,
            "text": baseline_response.text,
            "tool_calls": [asdict(c) for c in baseline_response.tool_calls],
        },
        attack={
            "prompt": scenario.attack_prompt,
            "text": attack_response.text,
            "tool_calls": [asdict(c) for c in attack_response.tool_calls],
        },
        state_before=state_before,
        state_after=state_after,
        validators=validator_results,
        evidence={"platform_marker": marker},
    )

    if ledger_path is not None:
        append_record(ledger_path, result.to_dict())

    return result
