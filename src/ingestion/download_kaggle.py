from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path


def download_dataset(dataset: str, output: Path) -> None:
    """Download and unzip a Kaggle dataset into an idempotent raw-data directory."""
    output.mkdir(parents=True, exist_ok=True)
    if shutil.which("kaggle") is None:
        raise RuntimeError("The Kaggle CLI is not installed. Run: pip install kaggle")
    if not os.getenv("KAGGLE_USERNAME") or not os.getenv("KAGGLE_KEY"):
        raise RuntimeError(
            "Set KAGGLE_USERNAME and KAGGLE_KEY, or configure ~/.kaggle/kaggle.json."
        )

    command = [
        "kaggle",
        "datasets",
        "download",
        "-d",
        dataset,
        "-p",
        str(output),
        "--unzip",
        "--force",
    ]
    subprocess.run(command, check=True)

    csv_files = sorted(output.glob("*.csv"))
    if not csv_files:
        raise RuntimeError(f"No CSV files were downloaded to {output}")
    print(f"Downloaded {len(csv_files)} CSV files to {output}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download the Olist Kaggle dataset")
    parser.add_argument("--dataset", default="olistbr/brazilian-ecommerce")
    parser.add_argument("--output", type=Path, default=Path("data/raw"))
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    download_dataset(args.dataset, args.output)
