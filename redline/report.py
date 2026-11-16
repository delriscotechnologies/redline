import json
import os
import re
import tempfile
from pathlib import Path

from .models import MAX_BYTES, parse_json, read_json, read_text
from .runner import verify_record


def to_json(value):
    return json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)


def save_record(directory, record):
    verify_record(record)
    directory = Path(directory)
    if directory.suffix.lower() == ".jsonl":
        raise ValueError("JSONL is read-only; use --store evidence for new runs")
    if not re.fullmatch(r"[0-9a-f]{32}", record["run_id"]):
        raise ValueError("invalid run ID")
    data = (to_json(record) + "\n").encode("utf-8")
    if len(data) > MAX_BYTES:
        raise ValueError("record exceeds the readable size limit")
    directory.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=directory, prefix=".", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, directory / f"{record['run_id']}.json")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def read_record(store, run_id):
    store = Path(store)
    if store.is_dir():
        if not re.fullmatch(r"[0-9a-f]{32}", run_id):
            raise ValueError("invalid run ID")
        record = read_json(store / f"{run_id}.json")
        if not isinstance(record, dict) or record.get("run_id") != run_id:
            raise ValueError("record run ID mismatch")
        return verify_record(record)
    if store.suffix.lower() != ".jsonl":
        raise ValueError("store must be a run directory or a legacy JSONL file")
    records = []
    seen = set()
    for number, line in enumerate(read_text(store).splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = parse_json(line)
            if not isinstance(record, dict) or not isinstance(record.get("run_id"), str) or not record["run_id"]:
                raise ValueError("entry needs a run_id")
            if record["run_id"] in seen:
                raise ValueError("duplicate run ID")
        except ValueError as exc:
            raise ValueError(f"{store}:{number}: invalid legacy ledger: {exc}") from exc
        records.append(record)
        seen.add(record["run_id"])
    return next((record for record in records if record["run_id"] == run_id), None)


def to_markdown(record):
    if record.get("schema_version") == 1:
        fields = [("Summary", {key: record.get(key) for key in
                              ("run_id", "adapter", "mode", "recorded_at", "tool_version")}),
                  ("Evaluation", record["evaluation"]), ("Provenance", record["provenance"]),
                  ("Scenario", record["scenario"]), ("Trace", record["trace"]), ("Integrity", record["integrity"])]
    else:
        fields = [("Legacy record (unverified)", record)]
    parts = ["# Redline report"]
    for title, value in fields:
        text = to_json(value)
        fence = "`" * max(3, 1 + max((len(match) for match in re.findall(r"`+", text)), default=0))
        parts.extend((f"## {title}", f"{fence}json\n{text}\n{fence}"))
    return "\n\n".join(parts) + "\n"
