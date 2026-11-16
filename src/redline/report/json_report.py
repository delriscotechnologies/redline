"""JSON report."""

from __future__ import annotations

import json
from typing import Any


def to_json(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2)
