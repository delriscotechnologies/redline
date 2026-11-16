import argparse
from dataclasses import asdict

from .catalog import get_technique, list_techniques
from .mock import MockAdapter
from .report import read_records, to_json, to_markdown
from .runner import Scope, load_scenario, run_scenario


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="redline", description="Synthetic AI-agent boundary evaluation.")
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("catalog", help="reference technique catalog")
    catalog_commands = catalog.add_subparsers(dest="catalog_command", required=True)
    catalog_commands.add_parser("list", help="list reference techniques")
    catalog_commands.add_parser("show", help="show one technique").add_argument("technique")
    for name in ("run", "selftest"):
        command = commands.add_parser(name, help="run a scenario" if name == "run" else "check both demo modes")
        command.add_argument("--scenario", help="scenario JSON; default: packaged demo")
        if name == "run":
            command.add_argument("--mode", choices=("vulnerable", "contained"), default="vulnerable")
            command.add_argument("--ledger", default="evidence/runs.jsonl")
    report = commands.add_parser("report", help="read a recorded run")
    report.add_argument("--run", required=True)
    report.add_argument("--format", choices=("markdown", "json"), default="markdown")
    report.add_argument("--ledger", default="evidence/runs.jsonl")
    return parser


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
            record = next((r for r in read_records(args.ledger) if r.get("run_id") == args.run), None)
            if record is None:
                raise ValueError(f"run not found: {args.run}")
            print(to_markdown(record) if args.format == "markdown" else to_json(record))
        else:
            scenario = load_scenario(args.scenario)
            modes = ("vulnerable", "contained") if args.command == "selftest" else (args.mode,)
            passed = True
            for mode in modes:
                result = run_scenario(
                    scenario, MockAdapter(complies_with_injections=mode == "vulnerable"), Scope(),
                    mode=mode, ledger_path=args.ledger if args.command == "run" else None,
                )
                if args.command == "run":
                    print(to_json(result.to_dict()))
                else:
                    print(f"[{mode}] {result.status}")
                    for check in result.validators:
                        print(f"   - {check.name}: {check.outcome} — {check.detail}")
                    passed &= result.status == ("Confirmed" if mode == "vulnerable" else "No breach observed")
            return 0 if passed else 1
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(1, f"redline: {exc}\n")
    return 0
