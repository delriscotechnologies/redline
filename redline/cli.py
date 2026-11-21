import argparse
import sys
from importlib.resources import files
from pathlib import Path

from .models import load_scenario, read_json
from .report import read_record, save_record, to_json, to_markdown
from .runner import compare_records, make_record, verify_record
from .trace import load_trace

FAIL_ON = {"confirmed": "Confirmed", "attempt": "Attempt observed", "inconclusive": "Inconclusive"}


def build_parser():
    parser = argparse.ArgumentParser(prog="redline", description="Guided AI-agent assessments and offline evidence evaluation.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("guide", help="print the assessment playbook for an evaluator agent")
    validate = commands.add_parser("validate", help="check a scenario and optional capture without running or saving it")
    validate.add_argument("--scenario", required=True)
    validate.add_argument("--trace")
    run = commands.add_parser("run", help="evaluate a captured trace")
    run.add_argument("--scenario", required=True)
    run.add_argument("--trace", required=True)
    run.add_argument("--store", default="evidence")
    run.add_argument("--fail-on", nargs="+", choices=(*FAIL_ON, "none"), default=["none"])
    report = commands.add_parser("report")
    report.add_argument("--run", required=True)
    report.add_argument("--store", "--ledger", default="evidence")
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.add_argument("--verify", action="store_true", help="require a verifiable record; new records are always verified")
    compare = commands.add_parser("compare")
    compare.add_argument("--before", required=True)
    compare.add_argument("--after", required=True)
    compare.add_argument("--store", default="evidence")
    return parser


def _record(store, run_id):
    record = read_record(store, run_id)
    if record is None:
        raise ValueError(f"run not found: {run_id}")
    return record


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "guide":
            print(files("redline").joinpath("SKILL.md").read_text(encoding="utf-8"), end="")
        elif args.command == "validate":
            scenario = load_scenario(args.scenario)
            if args.trace:
                load_trace(args.trace, scenario)
            print(to_json({"valid": True, "scenario_id": scenario.id, "capture_checked": bool(args.trace)}))
        elif args.command == "run":
            if "none" in args.fail_on and len(args.fail_on) > 1:
                raise ValueError("--fail-on none cannot be combined with other verdicts")
            scenario = load_scenario(args.scenario)
            trace = read_json(args.trace)
            record = make_record(scenario, trace, adapter="trace", source_name=Path(args.trace).name)
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
