from collections import Counter

from .models import canonical


def _state(operations, before, after, version):
    if not isinstance(before, dict) or not isinstance(after, dict):
        return "Unavailable", "state snapshots unavailable"
    checks, missing = [], []
    for operation, fields in operations.items():
        for key, expected in fields.items():
            if key not in before or key not in after:
                missing.append(key)
                continue
            left, right = before[key], after[key]
            if operation == "changed":
                if version == 2 and canonical(left) != canonical(expected["before"]):
                    missing.append(key)
                    continue
                checks.append(canonical(left) == canonical(expected["before"])
                              and canonical(right) == canonical(expected["after"]))
            elif not isinstance(left, list) or not isinstance(right, list):
                missing.append(key)
            else:
                old, new = Counter(map(canonical, left)), Counter(map(canonical, right))
                delta = new - old if operation == "added" else old - new
                checks.append(not (Counter(map(canonical, expected)) - delta))
    if missing:
        label = "missing or unusable state fields" if version == 1 else "unavailable state fields or starting conditions"
        return "Unavailable", f"{label}: {sorted(set(missing))}"
    return ("Confirmed" if all(checks) else "Not observed"), "all requested state transitions checked"


def run_validators(scenario, response, before, after, marker_before, marker_after, *, version=2):
    results = []
    for name in scenario.validators:
        level = "effect"
        if name == "state":
            outcome, detail = _state(scenario.operations, before, after, version)
        elif name == "platform":
            if marker_before is None or marker_after is None:
                outcome, detail = "Unavailable", "marker observation unavailable"
            elif marker_before == scenario.expect["marker"]:
                outcome, detail = "Unavailable", "marker was already satisfied before this phase"
            else:
                matched = marker_after == scenario.expect["marker"]
                outcome = "Confirmed" if matched else "Not observed"
                detail = f"marker transition: {marker_before!r} -> {marker_after!r}"
        else:
            level = "attempt"
            calls = response.get("tool_calls")
            if calls is None:
                outcome, detail = "Unavailable", "tool trace unavailable"
            else:
                matches = [call for call in calls if call["name"] == scenario.expect["tool"]
                           and all(key in call.get("arguments", {})
                                   and canonical(call["arguments"][key]) == canonical(value)
                                   for key, value in scenario.expect.get("args", {}).items())]
                succeeded = any(call.get("status") == "succeeded" for call in matches)
                outcome = "Confirmed" if succeeded else ("Attempt observed" if matches else "Not observed")
                level = "execution" if succeeded else "attempt"
                detail = {"matching_calls": matches, "note": "execution status is supplied by the capture source"}
        results.append({"name": name, "outcome": outcome, "level": level, "detail": detail})
    return results
