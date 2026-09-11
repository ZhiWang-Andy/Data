import json
from pathlib import Path

import pytest

from src.maintenance.quality import assert_quality, evaluate_count, evaluate_rate, write_report


def test_quality_report_passes(tmp_path: Path) -> None:
    report_path = tmp_path / "quality.json"
    report = write_report(
        [evaluate_count("rows", 10), evaluate_rate("missing", 0, 10, 0.01)],
        report_path,
    )
    assert report["status"] == "PASS"
    assert json.loads(report_path.read_text())["status"] == "PASS"
    assert_quality(report)


def test_quality_gate_raises(tmp_path: Path) -> None:
    report = write_report([evaluate_count("rows", 0)], tmp_path / "quality.json")
    with pytest.raises(RuntimeError):
        assert_quality(report)
