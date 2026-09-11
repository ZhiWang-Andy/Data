from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    observed: Any
    expectation: str


def evaluate_count(name: str, observed: int, minimum: int = 1) -> CheckResult:
    return CheckResult(
        name=name,
        status="PASS" if observed >= minimum else "FAIL",
        observed=observed,
        expectation=f">= {minimum}",
    )


def evaluate_rate(name: str, numerator: int, denominator: int, maximum: float) -> CheckResult:
    rate = 0.0 if denominator == 0 else numerator / denominator
    return CheckResult(
        name=name,
        status="PASS" if rate <= maximum else "FAIL",
        observed=round(rate, 6),
        expectation=f"<= {maximum}",
    )


def write_report(results: list[CheckResult], path: Path) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "status": "PASS" if all(result.status == "PASS" for result in results) else "FAIL",
        "checks": [asdict(result) for result in results],
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def assert_quality(payload: dict[str, Any]) -> None:
    if payload["status"] != "PASS":
        failed = [check["name"] for check in payload["checks"] if check["status"] == "FAIL"]
        raise RuntimeError(f"Data quality gate failed: {', '.join(failed)}")
