import pytest

from src.analytics.ab_testing import sample_ratio_mismatch, two_proportion_test


def test_two_proportion_test_detects_positive_lift() -> None:
    result = two_proportion_test(200, 1000, 250, 1000)
    assert result.absolute_lift == pytest.approx(0.05)
    assert result.relative_lift == pytest.approx(0.25)
    assert result.p_value < 0.05
    assert result.significant is True


def test_two_proportion_test_validates_counts() -> None:
    with pytest.raises(ValueError):
        two_proportion_test(11, 10, 5, 10)


def test_sample_ratio_mismatch_balanced() -> None:
    result = sample_ratio_mismatch(501, 499)
    assert result["srm_detected"] is False


def test_sample_ratio_mismatch_detects_large_imbalance() -> None:
    result = sample_ratio_mismatch(700, 300)
    assert result["srm_detected"] is True
