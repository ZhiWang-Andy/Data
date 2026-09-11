from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"last_successful_run": None, "processed_partitions": []}
    return json.loads(path.read_text(encoding="utf-8"))


def write_success(path: Path, partitions: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {
        "last_successful_run": datetime.now(UTC).isoformat(),
        "processed_partitions": sorted(set(partitions)),
    }
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")
