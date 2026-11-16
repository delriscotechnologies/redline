import argparse
import io
import json
import tempfile
from contextlib import redirect_stderr
from dataclasses import asdict, replace
from importlib.resources import files
from pathlib import Path

from .catalog import get_technique, list_techniques
from .mock import MockAdapter
from .report import append_record, read_records, to_json, to_markdown
from .runner import Scope, load_scenario, run_scenario
from .trace import TraceAdapter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="redline", description="AI-agent boundary evaluation.")
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog", help="reference technique catalog")
    catalog_commands = catalog.add_subparsers(dest="catalog_command", required=True)
    catalog_commands.add_parser("list", help="list reference techniques")
    catalog_commands.add_parser("show", help="show one technique").add_argument("technique")
    run = commands.add_parser("run", help="run a scenario")
    run.add_argument("--scenario", help="scenario JSON; default: packaged demo")
    run.add_argument("--mode", choices=("vulnerable", "contained"), default="vulnerable")
    run.add_argument("--ledger", default="evidence/runs.jsonl")
    run.add_argument("--trace", help="captured trace JSON for the trace adapter")
    run.add_argument("--fail-on", choices=("none", "confirmed", "inconclusive"), default="none")
    selftest = commands.add_parser("selftest", help="check demo modes, trace and guards")
    selftest.add_argument("--scenario", help="scenario JSON; default: packaged demo")
    report = commands.add_parser("report", help="read a recorded run")
    report.add_argument("--run", required=True)
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.add_argument("--ledger", default="evidence/runs.jsonl")
    return parser


def _adapter(scenario, *, mode="vulnerable", trace=None):
    if scenario.adapter == "trace":
        if trace is None:
            raise ValueError("--trace is required for the trace adapter")
        return TraceAdapter.from_file(trace)
    if trace is not None:
        raise ValueError("--trace only applies to the trace adapter")
    return MockAdapter(complies_with_injections=mode == "vulnerable")


def _scope(scenario) -> Scope:
    if scenario.adapter == "mock":
        return Scope()
    return Scope(target=scenario.target, allowlist=(scenario.target,))


def _raises(exc, fn) -> bool:
    try:
        fn()
    except exc:
        return True
    return False


def cmd_selftest(args) -> int:
    ok = True

    def check(name, condition):
        nonlocal ok
        print(f"[{'PASS' if condition else 'FAIL'}] {name}")
        ok = ok and bool(condition)

    demo = load_scenario(args.scenario)
    for mode, expected in (("vulnerable", "Confirmed"), ("contained", "No breach observed")):
        result = run_scenario(demo, _adapter(demo, mode=mode), _scope(demo), mode=mode)
        check(f"demo {mode}", result.status == expected)

    trace_scenario = load_scenario(str(files("redline").joinpath("trace_scenario.json")))
    for mode, expected in (("vulnerable", "Confirmed"), ("contained", "No breach observed")):
        trace = json.loads(files("redline").joinpath(f"trace_{mode}.json").read_text(encoding="utf-8"))
        result = run_scenario(trace_scenario, TraceAdapter(trace), _scope(trace_scenario), mode=mode)
        check(f"trace {mode}", result.status == expected)

    result = run_scenario(demo, _adapter(demo), _scope(demo))
    detail = next(v.detail for v in result.validators if v.name == "tool_trace")
    check("tool evidence shows arguments", "'carlos'" in detail)
    check("identical prompts rejected",
          _raises(ValueError, lambda: replace(demo, attack_prompt=demo.baseline_prompt).validate()))
    check("unknown validator rejected", _raises(ValueError, lambda: replace(demo, validators=["nope"]).validate()))

    double = replace(demo, expect={**demo.expect, "state": {"deleted": ["carlos", "carlos"]}}, validators=["state"])
    result = run_scenario(double, _adapter(double), _scope(double))
    check("state counts additions", result.status == "No breach observed")

    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / "runs.jsonl"
        append_record(ledger, {"run_id": "old"})
        ledger.write_bytes(ledger.read_bytes()[:-1])
        check("append refuses truncated ledger", _raises(ValueError, lambda: append_record(ledger, {"run_id": "new"})))
        check("read keeps valid records", len(list(read_records(ledger))) == 1)
        with ledger.open("a", encoding="utf-8") as fh:
            fh.write("\n{bad json}\n")
        with redirect_stderr(io.StringIO()):
            check("read stops at invalid line", len(list(read_records(ledger))) == 1)
    return 0 if ok else 1


def cmd_run(args) -> int:
    scenario = load_scenario(args.scenario)
    result = run_scenario(scenario, _adapter(scenario, mode=args.mode, trace=args.trace),
                          _scope(scenario), mode=args.mode, ledger_path=args.ledger)
    print(to_json(result.to_dict()))
    if args.fail_on != "none" and result.status.lower() == args.fail_on:
        return 1
    return 0


def cmd_report(args) -> int:
    record = next((r for r in read_records(args.ledger) if r.get("run_id") == args.run), None)
    if record is None:
        raise ValueError(f"run not found: {args.run}")
    print(to_markdown(record) if args.format == "markdown" else to_json(record))
    return 0


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            if args.catalog_command == "list":
                for technique in list_techniques():
                    print(f"{technique.id:28} {technique.name}  [{technique.source}]")
            else:
                print(to_json(asdict(get_technique(args.technique))))
        elif args.command == "report":
            return cmd_report(args)
        elif args.command == "run":
            return cmd_run(args)
        else:
            return cmd_selftest(args)
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"redline: {exc}\n")
    return 0
