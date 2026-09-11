from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def retain_latest_runs(runs_root: Path, keep: int) -> list[Path]:
    runs = sorted(
        (path for path in runs_root.glob("run_*") if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    removed: list[Path] = []
    for stale in runs[keep:]:
        shutil.rmtree(stale)
        removed.append(stale)
    return removed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove stale pipeline run artifacts")
    parser.add_argument("--runs-root", type=Path, default=Path("artifacts/runs"))
    parser.add_argument("--keep", type=int, default=20)
    args = parser.parse_args()
    deleted = retain_latest_runs(args.runs_root, args.keep)
    print(f"Removed {len(deleted)} stale run directories")
