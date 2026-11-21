import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

VALIDATORS = ("tool_trace", "state", "platform")
MAX_BYTES = 8 * 1024 * 1024


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_json(text):
    def reject(value):
        raise ValueError(f"non-finite JSON number: {value}")
    value = json.loads(text, object_pairs_hook=_object, parse_constant=reject)
    canonical(value)
    return value


def read_text(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"{path}: input exceeds {MAX_BYTES} bytes")
    return raw.decode("utf-8")


def read_json(path):
    return parse_json(read_text(path))


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
    required_validators: list[str] | None = None

    @property
    def required(self):
        return self.validators if self.required_validators is None else self.required_validators

    @property
    def operations(self):
        state = self.expect.get("state", {})
        return {"added": state} if state and all(isinstance(v, list) for v in state.values()) else state

    def validate(self):
        for key in ("id", "technique_id", "adapter", "target", "baseline_prompt", "attack_prompt"):
            if not isinstance(getattr(self, key), str) or not getattr(self, key).strip():
                raise ValueError(f"{key} must be a nonempty string")
        if self.adapter != "trace":
            raise ValueError("adapter must be trace; use version 0.4.0 to read old mock records")
        if self.baseline_prompt == self.attack_prompt:
            raise ValueError("baseline and attack prompts must differ")
        for label, names in (("validators", self.validators), ("required_validators", self.required)):
            if (not isinstance(names, list) or not names
                    or any(not isinstance(v, str) or v not in VALIDATORS for v in names)
                    or len(set(names)) != len(names)):
                raise ValueError(f"{label} must contain unique supported validator names")
        if not set(self.required) <= set(self.validators):
            raise ValueError("required_validators must be selected validators")
        if not isinstance(self.expect, dict) or self.expect.keys() - {"tool", "args", "state", "marker"}:
            raise ValueError("expect supports tool, args, state and marker")
        if "tool_trace" in self.validators:
            if not isinstance(self.expect.get("tool"), str) or not self.expect["tool"].strip():
                raise ValueError("tool_trace requires a tool name")
            if not isinstance(self.expect.get("args", {}), dict):
                raise ValueError("args must be an object")
        if "state" in self.validators:
            if not isinstance(self.expect.get("state"), dict):
                raise ValueError("state expectations must be an object")
            operations = self.operations
            if not operations or operations.keys() - {"added", "removed", "changed"}:
                raise ValueError("state supports added, removed and changed")
            for operation, fields in operations.items():
                if not isinstance(fields, dict) or not fields:
                    raise ValueError(f"{operation} requires nonempty fields")
                for key, value in fields.items():
                    if not isinstance(key, str) or not key:
                        raise ValueError("state field names must be nonempty strings")
                    if operation == "changed":
                        if (not isinstance(value, dict) or set(value) != {"before", "after"}
                                or canonical(value["before"]) == canonical(value["after"])):
                            raise ValueError("changed requires distinct before and after values")
                    elif not isinstance(value, list) or not value:
                        raise ValueError(f"{operation} requires nonempty addition/removal lists")
        if "platform" in self.validators:
            if not isinstance(self.expect.get("marker"), str) or not self.expect["marker"].strip():
                raise ValueError("platform requires a marker string")
        canonical(asdict(self))


def load_scenario(path):
    data = read_json(path)
    if not isinstance(data, dict):
        raise ValueError("scenario must be an object")
    try:
        scenario = Scenario(**data)
    except TypeError as exc:
        raise ValueError(f"invalid scenario fields: {exc}") from exc
    scenario.validate()
    return scenario
