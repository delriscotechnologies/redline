"""Markdown report."""

from __future__ import annotations

from typing import Any


def to_markdown(record: dict[str, Any]) -> str:
    lines = [
        f"# Run {record.get('run_id', '-')}",
        "",
        f"- Scenario: `{record.get('scenario_id', '-')}`",
        f"- Technique: `{record.get('technique_id', '-')}`",
        f"- Target: `{record.get('target', '-')}`",
        f"- Mode: `{record.get('mode', '-')}`",
        f"- **Result: {record.get('status', '-')}**",
        "",
        "## Baseline",
        "",
        f"> {record.get('baseline', {}).get('prompt', '')}",
        "",
        f"{record.get('baseline', {}).get('text', '')}",
        "",
        "## Attack",
        "",
        f"> {record.get('attack', {}).get('prompt', '')}",
        "",
        f"{record.get('attack', {}).get('text', '')}",
        "",
        "## Validators",
        "",
    ]
    for v in record.get("validators", []):
        lines.append(f"- **{v['name']}**: {v['outcome']} — {v['detail']}")
    lines += ["", "## State", ""]
    lines.append(f"- before: `{record.get('state_before', {})}`")
    lines.append(f"- after: `{record.get('state_after', {})}`")
    lines.append("")
    return "\n".join(lines)
