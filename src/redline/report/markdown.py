"""Markdown report."""

from __future__ import annotations

from typing import Any


def to_markdown(record: dict[str, Any]) -> str:
    lines = [
        f"# Run {record.get('run_id', '-')}",
        "",
        f"- Escenario: `{record.get('scenario_id', '-')}`",
        f"- Técnica: `{record.get('technique_id', '-')}`",
        f"- Target: `{record.get('target', '-')}`",
        f"- Modo: `{record.get('mode', '-')}`",
        f"- **Resultado: {record.get('status', '-')}**",
        "",
        "## Baseline",
        "",
        f"> {record.get('baseline', {}).get('prompt', '')}",
        "",
        f"{record.get('baseline', {}).get('text', '')}",
        "",
        "## Ataque",
        "",
        f"> {record.get('attack', {}).get('prompt', '')}",
        "",
        f"{record.get('attack', {}).get('text', '')}",
        "",
        "## Validadores",
        "",
    ]
    for v in record.get("validators", []):
        lines.append(f"- **{v['name']}**: {v['outcome']} — {v['detail']}")
    lines += ["", "## Estado", ""]
    lines.append(f"- antes: `{record.get('state_before', {})}`")
    lines.append(f"- después: `{record.get('state_after', {})}`")
    lines.append("")
    return "\n".join(lines)
