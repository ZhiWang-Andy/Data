from __future__ import annotations

from dataclasses import asdict, dataclass
from math import sqrt

import numpy as np
from scipy.stats import chi2, norm


@dataclass(frozen=True)
class ProportionTestResult:
    control_rate: float
    treatment_rate: float
    absolute_lift: float
    relative_lift: float
    standard_error: float
    z_score: float
    p_value: float
    ci_low: float
    ci_high: float
    significant: bool

    def to_dict(self) -> dict[str, float | bool]:
        return asdict(self)


def two_proportion_test(
    control_successes: int,
    control_total: int,
    treatment_successes: int,
    treatment_total: int,
    alpha: float = 0.05,
) -> ProportionTestResult:
    if control_total <= 0 or treatment_total <= 0:
        raise ValueError("Both groups must have positive sample sizes")
    if not 0 <= control_successes <= control_total:
        raise ValueError("Control successes must be between zero and control total")
    if not 0 <= treatment_successes <= treatment_total:
        raise ValueError("Treatment successes must be between zero and treatment total")

    p_control = control_successes / control_total
    p_treatment = treatment_successes / treatment_total
    pooled = (control_successes + treatment_successes) / (control_total + treatment_total)
    pooled_se = sqrt(pooled * (1 - pooled) * (1 / control_total + 1 / treatment_total))
    z_score = 0.0 if pooled_se == 0 else (p_treatment - p_control) / pooled_se
    p_value = float(2 * (1 - norm.cdf(abs(z_score))))

    unpooled_se = sqrt(
        p_control * (1 - p_control) / control_total
        + p_treatment * (1 - p_treatment) / treatment_total
    )
    critical = float(norm.ppf(1 - alpha / 2))
    lift = p_treatment - p_control
    relative_lift = 0.0 if p_control == 0 else lift / p_control
    return ProportionTestResult(
        control_rate=p_control,
        treatment_rate=p_treatment,
        absolute_lift=lift,
        relative_lift=relative_lift,
        standard_error=unpooled_se,
        z_score=z_score,
        p_value=p_value,
        ci_low=lift - critical * unpooled_se,
        ci_high=lift + critical * unpooled_se,
        significant=bool(p_value < alpha),
    )


def sample_ratio_mismatch(
    control_total: int,
    treatment_total: int,
    expected_treatment_share: float = 0.5,
    alpha: float = 0.01,
) -> dict[str, float | bool]:
    total = control_total + treatment_total
    if total <= 0 or not 0 < expected_treatment_share < 1:
        raise ValueError("Invalid sample size or expected allocation")
    expected = np.array(
        [total * (1 - expected_treatment_share), total * expected_treatment_share],
        dtype=float,
    )
    observed = np.array([control_total, treatment_total], dtype=float)
    statistic = float(np.sum((observed - expected) ** 2 / expected))
    p_value = float(1 - chi2.cdf(statistic, df=1))
    return {
        "chi_square": statistic,
        "p_value": p_value,
        "srm_detected": bool(p_value < alpha),
    }
