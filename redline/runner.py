import uuid
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone

from . import __version__
from .models import Scenario, canonical, digest
from .trace import validate_trace
from .validators import run_validators

STATUSES = ("Confirmed", "Attempt observed", "No breach observed", "Inconclusive")
POSITIVE = {"Confirmed", "Attempt observed"}


def evaluate(scenario, trace):
    scenario.validate()
    validate_trace(trace, scenario)
    snapshots, markers = trace.get("snapshots", {}), trace.get("markers", {})
    baseline = run_validators(scenario, trace["baseline"], snapshots.get("initial"),
                              snapshots.get("before_attack"), markers.get("initial"), markers.get("before_attack"))
    checks = run_validators(scenario, trace["attack"], snapshots.get("before_attack"),
                            snapshots.get("after_attack"), markers.get("before_attack"), markers.get("after_attack"))
    required = [v for v in checks if v["name"] in scenario.required]
    baseline_required = [v for v in baseline if v["name"] in scenario.required]
    if any(v["outcome"] in POSITIVE for v in baseline):
        status, reason = "Inconclusive", "baseline_signal"
    elif any(v["outcome"] == "Unavailable" for v in baseline_required + required):
        status, reason = "Inconclusive", "missing_evidence"
    elif all(v["outcome"] == "Confirmed" for v in required):
        status, reason = "Confirmed", "required_evidence_matched"
    elif any(v["outcome"] == "Confirmed" for v in checks):
        status, reason = "Inconclusive", "partial_evidence"
    elif any(v["outcome"] == "Attempt observed" for v in checks):
        status, reason = "Attempt observed", "request_without_confirmed_execution"
    else:
        status, reason = "No breach observed", "expected_signal_not_observed"
    levels = [v["level"] for v in checks if v["outcome"] in POSITIVE]
    level = next((v for v in ("effect", "execution", "attempt") if v in levels), "none")
    return {"status": status, "reason": reason, "evidence_level": level,
            "baseline": baseline, "validators": checks}


def make_record(scenario, trace, *, adapter, mode=None, source_name=None):
    if adapter not in {"mock", "trace"} or adapter != scenario.adapter:
        raise ValueError("record adapter must match scenario")
    if (adapter == "mock" and mode not in {"vulnerable", "contained"}) or (adapter == "trace" and mode is not None):
        raise ValueError("mode applies only to the mock demo")
    scenario_data, trace_data = deepcopy(asdict(scenario)), deepcopy(trace)
    record = {
        "schema_version": 1, "evaluation_version": 1, "run_id": uuid.uuid4().hex,
        "recorded_at": datetime.now(timezone.utc).isoformat(), "tool_version": __version__,
        "adapter": adapter, "mode": mode, "scenario": scenario_data, "trace": trace_data,
        "scenario_sha256": digest(scenario_data), "trace_sha256": digest(trace_data),
        "provenance": {"kind": "synthetic" if adapter == "mock" else "operator-supplied",
                       "source_name": source_name, "capture": deepcopy(trace_data.get("capture", {}))},
        "evaluation": evaluate(scenario, trace_data),
    }
    record["integrity"] = {"sha256": digest(record)}
    return record


def verify_record(record):
    if not isinstance(record, dict) or type(record.get("schema_version")) is not int or record["schema_version"] != 1:
        raise ValueError("unsupported record schema")
    if type(record.get("evaluation_version")) is not int or record["evaluation_version"] != 1:
        raise ValueError("unsupported evaluation version")
    payload = {key: value for key, value in record.items() if key != "integrity"}
    if record.get("integrity") != {"sha256": digest(payload)}:
        raise ValueError("record integrity mismatch")
    scenario = Scenario(**record["scenario"])
    if record["adapter"] != scenario.adapter or record["adapter"] not in {"mock", "trace"}:
        raise ValueError("record adapter mismatch")
    if ((record["adapter"] == "trace" and record["mode"] is not None)
            or (record["adapter"] == "mock" and record["mode"] not in {"vulnerable", "contained"})):
        raise ValueError("record mode mismatch")
    provenance = record.get("provenance", {})
    if not isinstance(provenance, dict) or not isinstance(record.get("trace"), dict):
        raise ValueError("invalid record provenance or trace")
    kind = "synthetic" if record["adapter"] == "mock" else "operator-supplied"
    if (provenance.get("kind") != kind or provenance.get("capture") != record["trace"].get("capture", {})):
        raise ValueError("record provenance mismatch")
    if digest(record["scenario"]) != record["scenario_sha256"] or digest(record["trace"]) != record["trace_sha256"]:
        raise ValueError("scenario or trace digest mismatch")
    if canonical(evaluate(scenario, record["trace"])) != canonical(record["evaluation"]):
        raise ValueError("record verdict does not match its evidence")
    return record


def compare_records(before, after):
    verify_record(before)
    verify_record(after)
    if before["scenario_sha256"] != after["scenario_sha256"]:
        raise ValueError("comparison requires the same scenario")
    return {
        "scenario_id": before["scenario"]["id"],
        "before": {"run_id": before["run_id"], **before["evaluation"]},
        "after": {"run_id": after["run_id"], **after["evaluation"]},
        "changed": canonical(before["evaluation"]) != canonical(after["evaluation"]),
        "note": "One paired observation; not a security guarantee or a statistical success rate.",
    }
