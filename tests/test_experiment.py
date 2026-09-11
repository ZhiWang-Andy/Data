import pandas as pd

from src.analytics.experiment import analyze, generate_experiment


def sample_orders(n: int = 4000) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "order_id": [f"order-{i}" for i in range(n)],
            "payment_value": [100 + (i % 50) for i in range(n)],
            "freight_value": [10 + (i % 5) for i in range(n)],
            "delivery_days": [5 + (i % 20) for i in range(n)],
        }
    )


def test_randomization_is_deterministic() -> None:
    first = generate_experiment(sample_orders(100), seed=10)
    second = generate_experiment(sample_orders(100), seed=10)
    assert first["variant"].tolist() == second["variant"].tolist()
    assert first["converted"].tolist() == second["converted"].tolist()


def test_experiment_analysis_has_required_outputs() -> None:
    frame = generate_experiment(sample_orders(), absolute_lift=0.05)
    result = analyze(frame)
    assert result["decision"] in {"SHIP", "HOLD"}
    assert "primary_metric" in result
    assert "sample_ratio_mismatch" in result
    assert "guardrails" in result
