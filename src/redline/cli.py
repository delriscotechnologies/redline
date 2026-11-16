"""Command line interface."""

from __future__ import annotations

import argparse

from .adapters import InjectionRule, MockAdapter
from .catalog import get_technique, list_techniques
from .config import demo_scope
from .evidence import read_records
from .report import to_json, to_markdown
from .scenarios import load_scenario, run_scenario

DEMO_RULES = [
    InjectionRule(
        pattern=r"delete the user carlos",
        tool="delete_user",
        arguments={"username": "carlos"},
    )
]


def _print(obj) -> None:
    print(to_json(obj) if isinstance(obj, dict) else obj)


def cmd_catalog(args: argparse.Namespace) -> int:
    if args.catalog_command == "list":
        for t in list_techniques():
            print(f"{t.id:28} {t.name}  [{t.source}]")
        return 0
    t = get_technique(args.technique)
    print(f"# {t.name} (`{t.id}`)")
    print(f"\nHipótesis: {t.hypothesis}")
    print(f"\nSuperficie: {t.input_surface}")
    print(f"\nEvidencia esperada: {t.expected_evidence}")
    print(f"\nPrecondiciones: {', '.join(t.preconditions)}")
    print(f"Controles negativos: {'; '.join(t.negative_controls)}")
    print(f"Mapeos: {t.mappings}")
    print(f"Remediación: {t.remediation}")
    print(f"Modos de fallo: {'; '.join(t.failure_modes)}")
    print(f"Fuente: {t.source}")
    return 0


def _adapter_for(scenario, mode: str) -> MockAdapter:
    if scenario.adapter != "mock":
        raise SystemExit(f"adapter no implementado en el MVP: {scenario.adapter}")
    return MockAdapter(
        injection_rules=DEMO_RULES,
        complies_with_injections=(mode == "vulnerable"),
    )


def cmd_run(args: argparse.Namespace) -> int:
    scenario = load_scenario(args.scenario)
    adapter = _adapter_for(scenario, args.mode)
    result = run_scenario(
        scenario,
        adapter,
        demo_scope(scenario.target),
        mode=args.mode,
        ledger_path=args.ledger,
    )
    print(to_json(result.to_dict()))
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    scenario = load_scenario(args.scenario)
    for mode in ("vulnerable", "contained"):
        adapter = _adapter_for(scenario, mode)
        result = run_scenario(
            scenario, adapter, demo_scope(scenario.target), mode=mode
        )
        print(f"[{mode}] {result.status}")
        for v in result.validators:
            print(f"   - {v.name}: {v.outcome} — {v.detail}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    records = read_records(args.ledger)
    match = [r for r in records if r.get("run_id") == args.run]
    if not match:
        raise SystemExit(f"run no encontrado: {args.run}")
    record = match[-1]
    print(to_markdown(record) if args.format == "markdown" else to_json(record))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="redline",
        description="Evaluador de red-team para agentes de IA (CLI-first, sin dependencias).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_catalog = sub.add_parser("catalog", help="catálogo de técnicas")
    cat_sub = p_catalog.add_subparsers(dest="catalog_command", required=True)
    cat_sub.add_parser("list", help="lista técnicas")
    p_show = cat_sub.add_parser("show", help="detalle de una técnica")
    p_show.add_argument("technique")

    p_run = sub.add_parser("run", help="ejecuta un escenario")
    p_run.add_argument("--scenario", required=True)
    p_run.add_argument("--mode", choices=["vulnerable", "contained"], default="vulnerable")
    p_run.add_argument(
        "--ledger",
        default="evidence/runs.jsonl",
        help="ruta del ledger JSONL (append-only)",
    )

    p_selftest = sub.add_parser("selftest", help="demo de extremo a extremo")
    p_selftest.add_argument(
        "--scenario", default="scenarios/excessive_agency.json"
    )

    p_report = sub.add_parser("report", help="reporte de un run")
    p_report.add_argument("--run", required=True)
    p_report.add_argument("--format", choices=["markdown", "json"], default="markdown")
    p_report.add_argument("--ledger", default="evidence/runs.jsonl")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "catalog":
        return cmd_catalog(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "selftest":
        return cmd_selftest(args)
    if args.command == "report":
        return cmd_report(args)
    parser.error("comando no reconocido")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
