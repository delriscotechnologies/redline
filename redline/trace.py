from datetime import datetime

from .models import canonical, read_json

PHASES = ("initial", "before_attack", "after_attack")
CALL_STATUSES = {"requested", "blocked", "succeeded", "failed"}


def validate_trace(trace, scenario):
    if not isinstance(trace, dict):
        raise ValueError("trace must be an object")
    for name in ("target", "baseline_prompt", "attack_prompt"):
        if trace.get(name) != getattr(scenario, name):
            raise ValueError(f"trace {name} does not match scenario")
    version = trace.get("schema_version", 1)
    if type(version) is not int or version != 1:
        raise ValueError("unsupported trace schema_version")
    for phase in ("baseline", "attack"):
        response = trace.get(phase)
        if not isinstance(response, dict) or not isinstance(response.get("text", ""), str):
            raise ValueError(f"trace {phase} must be a response object")
        calls = response.get("tool_calls")
        if calls is not None:
            if not isinstance(calls, list):
                raise ValueError("tool_calls must be a list or null")
            for call in calls:
                if (not isinstance(call, dict) or not isinstance(call.get("name"), str)
                        or not call["name"].strip() or not isinstance(call.get("arguments", {}), dict)
                        or not isinstance(call.get("status", "requested"), str)
                        or call.get("status", "requested") not in CALL_STATUSES):
                    raise ValueError("invalid tool call: expected name, object arguments and supported status")
    for name in ("snapshots", "markers"):
        values = trace.get(name, {})
        if not isinstance(values, dict):
            raise ValueError(f"{name} must be an object")
        for phase in PHASES:
            value = values.get(phase)
            if value is not None and not isinstance(value, dict if name == "snapshots" else str):
                raise ValueError(f"invalid {name}.{phase}")
    capture = trace.get("capture", {})
    if not isinstance(capture, dict) or capture.keys() - {"source", "id", "captured_at"}:
        raise ValueError("capture supports source, id and captured_at")
    for name, value in capture.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"capture.{name} must be a nonempty string")
    if "captured_at" in capture:
        timestamp = datetime.fromisoformat(capture["captured_at"].replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            raise ValueError("capture timestamp must include a timezone")
    canonical(trace)


def load_trace(path, scenario):
    trace = read_json(path)
    validate_trace(trace, scenario)
    return trace
