import json
import re
import sys
from pathlib import Path


def to_json(record) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False)


def append_record(path, record) -> None:
    path = Path(path)
    data = (json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size:
        with path.open("rb") as fh:
            fh.seek(-1, 2)
            if fh.read(1) != b"\n":
                raise ValueError(f"{path}: incomplete final ledger line; repair before appending")
            fh.seek(0)
            last = None
            for line in fh:
                if line.strip():
                    last = line
        try:
            json.loads(last)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ValueError(f"{path}: incomplete final record; repair before appending") from exc
    with path.open("ab") as fh:
        fh.write(data)


def read_records(path):
    path = Path(path)
    if not path.exists():
        return
    with path.open(encoding="utf-8") as fh:
        for number, line in enumerate(fh, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                print(f"redline: {path}:{number}: invalid ledger JSON; stopping", file=sys.stderr)
                return
            if not isinstance(record, dict):
                print(f"redline: {path}:{number}: ledger entry is not an object; stopping", file=sys.stderr)
                return
            yield record


def to_markdown(record) -> str:
    summary = {k: record.get(k) for k in
               ("run_id", "scenario_id", "technique_id", "target", "mode", "status")}
    parts = ["# Redline report"]
    for title, value in (
        ("Summary", summary), ("Baseline", record.get("baseline", {})),
        ("Attack", record.get("attack", {})), ("Validators", record.get("validators", [])),
        ("State", {"before_attack": record.get("state_before"), "after_attack": record.get("state_after")}),
        ("Evidence", record.get("evidence", {})),
    ):
        text = to_json(value)
        fence = "`" * max(3, 1 + max((len(m) for m in re.findall(r"`+", text)), default=0))
        parts.extend((f"## {title}", f"{fence}json\n{text}\n{fence}"))
    return "\n\n".join(parts) + "\n"
