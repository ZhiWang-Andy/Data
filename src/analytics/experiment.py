from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from src.analytics.ab_testing import sample_ratio_mismatch, two_proportion_test


def stable_uniform(value: str, seed: int) -> float:
    digest = hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()
    return int(digest[:16], 16) / float(16**16 - 1)


def generate_experiment(
    orders: pd.DataFrame,
    seed: int = 20260910,
    treatment_share: float = 0.5,
    absolute_lift: float = 0.025,
) -> pd.DataFrame:
    """Create a synthetic randomized experiment on real Olist covariate distributions.

    The conversion outcome is simulated and must not be interpreted as an actual
    historical Olist experiment.
    """
    columns = ["order_id", "payment_value", "freight_value", "delivery_days"]
    missing = set(columns) - set(orders.columns)
    if missing:
        raise ValueError(f"Missing experiment columns: {sorted(missing)}")

    frame = orders[columns].copy()
    frame["assignment_u"] = frame["order_id"].astype(str).map(
        lambda value: stable_uniform(value, seed)
    )
    frame["variant"] = np.where(
        frame["assignment_u"] < treatment_share,
        "treatment",
        "control",
    )

    payment = pd.to_numeric(frame["payment_value"], errors="coerce").fillna(0).clip(0, 1000)
    freight = pd.to_numeric(frame["freight_value"], errors="coerce").fillna(0).clip(0, 300)
    delivery = pd.to_numeric(frame["delivery_days"], errors="coerce").fillna(12).clip(0, 90)

    # A transparent data-generating process for demonstration only.
    baseline = 0.20 + 0.00003 * payment - 0.00012 * freight
    probability = np.clip(
        baseline + absolute_lift * (frame["variant"] == "treatment").astype(float),
        0.02,
        0.95,
    )
    frame["outcome_u"] = frame["order_id"].astype(str).map(
        lambda value: stable_uniform(value, seed + 1)
    )
    frame["converted"] = (frame["outcome_u"] < probability).astype(int)
    frame["order_value_guardrail"] = payment
    frame["delivery_days_guardrail"] = delivery
    frame["simulated_conversion_probability"] = probability
    return frame


def analyze(frame: pd.DataFrame, alpha: float = 0.05) -> dict:
    summary = frame.groupby("variant").agg(
        users=("order_id", "count"),
        conversions=("converted", "sum"),
        conversion_rate=("converted", "mean"),
        average_order_value=("order_value_guardrail", "mean"),
        average_delivery_days=("delivery_days_guardrail", "mean"),
    )
    if not {"control", "treatment"}.issubset(summary.index):
        raise ValueError("Experiment must contain control and treatment rows")

    control = summary.loc["control"]
    treatment = summary.loc["treatment"]
    test = two_proportion_test(
        int(control["conversions"]),
        int(control["users"]),
        int(treatment["conversions"]),
        int(treatment["users"]),
        alpha=alpha,
    )
    srm = sample_ratio_mismatch(int(control["users"]), int(treatment["users"]))
    return {
        "experiment_name": "checkout_reassurance_banner",
        "data_note": "Synthetic randomized outcome layer built on real Olist covariates.",
        "alpha": alpha,
        "primary_metric": test.to_dict(),
        "sample_ratio_mismatch": srm,
        "guardrails": {
            "control_average_order_value": float(control["average_order_value"]),
            "treatment_average_order_value": float(treatment["average_order_value"]),
            "absolute_aov_change": float(
                treatment["average_order_value"] - control["average_order_value"]
            ),
            "control_average_delivery_days": float(control["average_delivery_days"]),
            "treatment_average_delivery_days": float(treatment["average_delivery_days"]),
        },
        "decision": (
            "SHIP"
            if test.significant and test.absolute_lift > 0 and not srm["srm_detected"]
            else "HOLD"
        ),
    }


def run(fact_orders_path: Path, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    orders = pd.read_parquet(fact_orders_path)
    experiment = generate_experiment(orders)
    result = analyze(experiment)
    experiment.to_parquet(output / "experiment_assignments.parquet", index=False)
    pd.DataFrame([result["primary_metric"]]).to_csv(
        output / "experiment_metrics.csv",
        index=False,
    )
    (output / "experiment_result.json").write_text(
        json.dumps(result, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(result, indent=2))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate and analyze the experiment layer")
    parser.add_argument("--fact-orders", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(args.fact_orders, args.output)
