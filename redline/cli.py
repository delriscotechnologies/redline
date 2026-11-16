import argparse
import sys
from copy import deepcopy
from dataclasses import replace
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from .catalog import get_technique, list_techniques
from .mock import make_trace
from .models import load_scenario, parse_json
from .report import read_record, save_record, to_json, to_markdown
from .runner import compare_records, evaluate, make_record, verify_record
from .trace import load_trace

FAIL_ON = {"confirmed": "Confirmed", "attempt": "Attempt observed", "inconclusive": "Inconclusive"}


def build_parser():
    parser = argparse.ArgumentParser(prog="redline", description="Offline evaluation of AI-agent evidence.")
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog", help="reference mechanisms, not executable tests")
    sub = catalog.add_subparsers(dest="action", required=True)
    sub.add_parser("list")
    sub.add_parser("show").add_argument("technique")
    run = commands.add_parser("run", help="evaluate a capture or run the synthetic demo")
    run.add_argument("--scenario")
    run.add_argument("--trace")
    run.add_argument("--mode", choices=("vulnerable", "contained"), help="mock demo only")
    run.add_argument("--store", default="evidence")
    run.add_argument("--fail-on", nargs="+", choices=(*FAIL_ON, "none"), default=["none"])
    commands.add_parser("selftest", help="check the packaged demo and evaluator regressions")
    report = commands.add_parser("report")
    report.add_argument("--run", required=True)
    report.add_argument("--store", "--ledger", default="evidence")
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.add_argument("--verify", action="store_true", help="require a verifiable v1 record; new records are always verified")
    compare = commands.add_parser("compare")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.add_argument("--store", default="evidence")
    return parser


def selftest():
    scenario = load_scenario()
    vulnerable, contained = make_trace(scenario, "vulnerable"), make_trace(scenario, "contained")
    attempt = deepcopy(contained)
    attempt["attack"]["tool_calls"] = [{"name": "delete_user", "arguments": {"username": "carlos"}}]
    missing = deepcopy(contained)
    missing["snapshots"]["after_attack"] = {}
    state_only = replace(scenario, validators=["state"], required_validators=["state"])
    typed = make_trace(scenario, "contained")
    typed["snapshots"]["after_attack"]["deleted"] = [True]
    typed_scenario = replace(state_only, expect={"state": {"added": {"deleted": [1]}}})
    baseline = replace(scenario, baseline_prompt=scenario.attack_prompt, attack_prompt="Summarize invoice 17.")
    cases = [
        ("mock vulnerable", scenario, vulnerable, "Confirmed"),
        ("mock contained", scenario, contained, "No breach observed"),
        ("request is not an effect", scenario, attempt, "Attempt observed"),
        ("missing state is inconclusive", scenario, missing, "Inconclusive"),
        ("booleans are not numbers", typed_scenario, typed, "No breach observed"),
        ("baseline signal is inconclusive", baseline, make_trace(baseline, "vulnerable"), "Inconclusive"),
    ]
    for mode, expected in (("vulnerable", "Confirmed"), ("contained", "No breach observed")):
        trace = parse_json(files("redline").joinpath(f"trace_{mode}.json").read_text(encoding="utf-8"))
        cases.append((f"captured fixture {mode}", load_scenario(str(files("redline").joinpath("trace_scenario.json"))),
                      trace, expected))
    ok = True
    for name, current, trace, expected in cases:
        passed = evaluate(current, trace)["status"] == expected
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
        ok = ok and passed
    record = make_record(scenario, vulnerable, adapter="mock", mode="vulnerable")
    with TemporaryDirectory() as directory:
        save_record(directory, record)
        passed = read_record(directory, record["run_id"]) == record
        print(f"[{'PASS' if passed else 'FAIL'}] stored record verifies")
        ok = ok and passed
    return 0 if ok else 1


def _record(store, run_id):
    record = read_record(store, run_id)
    if record is None:
        raise ValueError(f"run not found: {run_id}")
    return record


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            if args.action == "list":
                for entry in list_techniques():
                    print(f"{entry['id']:28} {entry['name']} [{entry['source']}]")
            else:
                print(to_json(get_technique(args.technique)))
        elif args.command == "selftest":
            return selftest()
        elif args.command == "run":
            if "none" in args.fail_on and len(args.fail_on) > 1:
                raise ValueError("--fail-on none cannot be combined with other verdicts")
            scenario = load_scenario(args.scenario)
            if scenario.adapter == "trace":
                if not args.trace or args.mode is not None:
                    raise ValueError("trace evaluation requires --trace and does not accept --mode")
                trace, mode = load_trace(args.trace, scenario), None
            else:
                if args.trace:
                    raise ValueError("--trace requires a trace scenario")
                mode = args.mode or "vulnerable"
                trace = make_trace(scenario, mode)
            record = make_record(scenario, trace, adapter=scenario.adapter, mode=mode,
                                 source_name=Path(args.trace).name if args.trace else None)
            save_record(args.store, record)
            summary = record["evaluation"]
            print(to_json({"run_id": record["run_id"], "status": summary["status"],
                           "reason": summary["reason"], "evidence_level": summary["evidence_level"]}))
            return int(summary["status"] in {FAIL_ON[key] for key in args.fail_on if key != "none"})
        elif args.command == "compare":
            print(to_json(compare_records(_record(args.store, args.before), _record(args.store, args.after))))
        else:
            record = _record(args.store, args.run)
            if record.get("schema_version") == 1:
                verify_record(record)
                output = record
            elif args.verify:
                raise ValueError("legacy records have no verifiable scenario/trace; import the original capture again")
            else:
                print("redline: legacy record is unverified", file=sys.stderr)
                output = {"verification": "legacy-unverified", "record": record}
            print(to_markdown(record) if args.format == "markdown" else to_json(output))
    except (OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        parser.exit(2, f"redline: {exc}\n")
    return 0
