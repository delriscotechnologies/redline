import hashlib
import json
import uuid
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from . import __version__
from .catalog import get_technique
from .models import MOCK_TARGET, TargetAdapter
from .report import append_record
from .validators import VALIDATORS, run_validators


@dataclass(frozen=True)
class Scope:
    target: str = MOCK_TARGET
    allowlist: tuple[str, ...] = (MOCK_TARGET,)
    max_requests: int = 10

    def allows(self, target: str) -> bool:
        return target == self.target and target in self.allowlist


@dataclass
class Scenario:
    id: str
    technique_id: str
    adapter: str
    target: str
    baseline_prompt: str
    attack_prompt: str
    expect: dict
    validators: list[str] = field(default_factory=lambda: list(VALIDATORS))

    def validate(self) -> None:
        for name in ("id", "technique_id", "adapter", "target", "baseline_prompt", "attack_prompt"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be a nonempty string")
        get_technique(self.technique_id)
        if self.adapter != "mock" or self.target != MOCK_TARGET:
            raise ValueError(f"only mock at {MOCK_TARGET} is supported")
        if (not isinstance(self.validators, list) or not self.validators
                or any(not isinstance(v, str) or v not in VALIDATORS for v in self.validators)
                or len(set(self.validators)) != len(self.validators)):
            raise ValueError("validators must be a nonempty list of unique supported names")
        if not isinstance(self.expect, dict) or self.expect.keys() - {"tool", "args", "state", "marker"}:
            raise ValueError("expect must contain only tool, args, state or marker")
        if "tool_trace" in self.validators:
            if not isinstance(self.expect.get("tool"), str) or not self.expect["tool"]:
                raise ValueError("tool_trace requires a tool name")
            if not isinstance(self.expect.get("args", {}), dict):
                raise ValueError("expected args must be an object")
        if "state" in self.validators:
            state = self.expect.get("state")
            if (not isinstance(state, dict) or not state
                    or any(not isinstance(k, str) or not isinstance(v, list) or not v
                           for k, v in state.items())):
                raise ValueError("state requires a nonempty object of nonempty addition lists")
        if "platform" in self.validators:
            if not isinstance(self.expect.get("marker"), str) or not self.expect["marker"]:
                raise ValueError("platform requires a nonempty marker")
        json.dumps(asdict(self), allow_nan=False)


@dataclass
class RunResult:
    run_id: str
    scenario_id: str
    technique_id: str
    target: str
    mode: str
    status: str
    baseline: dict
    attack: dict
    state_before: dict
    state_after: dict
    validators: list
    evidence: dict

    def to_dict(self) -> dict:
        return asdict(self)


def load_scenario(path=None) -> Scenario:
    text = Path(path).read_text(encoding="utf-8") if path is not None else (
        files("redline").joinpath("excessive_agency.json").read_text(encoding="utf-8")
    )
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("scenario must be a JSON object")
    try:
        scenario = Scenario(**data)
    except TypeError as exc:
        raise ValueError(f"invalid scenario fields: {exc}") from exc
    scenario.validate()
    return scenario


def run_scenario(scenario: Scenario, adapter: TargetAdapter, scope: Scope, *,
                 mode="vulnerable", ledger_path=None) -> RunResult:
    scenario.validate()
    if mode not in {"vulnerable", "contained"}:
        raise ValueError("mode must be vulnerable or contained")
    if not scope.allows(scenario.target) or adapter.name != scenario.adapter or adapter.target != scenario.target:
        raise ValueError("target or adapter is outside the authorized scope")
    if type(scope.max_requests) is not int or scope.max_requests < 2:
        raise ValueError("this run requires a budget of at least two requests")
    initial = deepcopy(adapter.snapshot())
    initial_marker = adapter.platform_marker()
    baseline = adapter.send(scenario.baseline_prompt)
    before = deepcopy(adapter.snapshot())
    marker_before = adapter.platform_marker()
    baseline_checks = run_validators(scenario, attack=baseline, state_before=initial,
                                    state_after=before, marker_before=initial_marker, marker=marker_before)
    attack = adapter.send(scenario.attack_prompt)
    after = deepcopy(adapter.snapshot())
    marker = adapter.platform_marker()
    checks = run_validators(scenario, attack=attack, state_before=before, state_after=after,
                            marker_before=marker_before, marker=marker)
    status = "Confirmed" if any(v.outcome == "Confirmed" for v in checks) else "No breach observed"
    if any(v.outcome == "Confirmed" for v in baseline_checks):
        status = "Inconclusive"
    result = RunResult(
        run_id=uuid.uuid4().hex, scenario_id=scenario.id, technique_id=scenario.technique_id,
        target=scenario.target, mode=mode, status=status,
        baseline={"prompt": scenario.baseline_prompt, **asdict(baseline),
                  "state_before": initial, "validators": [asdict(v) for v in baseline_checks]},
        attack={"prompt": scenario.attack_prompt, **asdict(attack)},
        state_before=before, state_after=after, validators=checks,
        evidence={"recorded_at": datetime.now(timezone.utc).isoformat(), "tool_version": __version__,
                  "scenario_sha256": hashlib.sha256(
                      json.dumps(asdict(scenario), sort_keys=True, allow_nan=False).encode()).hexdigest(),
                  "platform_marker_before": marker_before, "platform_marker_after": marker},
    )
    if ledger_path is not None:
        append_record(ledger_path, result.to_dict())
    return result
