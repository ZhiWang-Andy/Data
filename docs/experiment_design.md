# Experiment design: checkout reassurance banner

## Objective

Evaluate whether a hypothetical checkout reassurance banner increases completed checkout conversion without reducing average order value or worsening delivery-related guardrails.

## Important data note

Olist is historical order data, not a randomized product experiment. This repository creates a **synthetic randomized experiment layer** using real Olist covariate distributions. The purpose is to demonstrate correct experimentation code and reporting, not to claim a real Olist treatment effect.

## Design

- Unit of randomization: order-like exposure
- Variants: control and treatment
- Allocation: 50/50, assigned with a stable SHA-256 hash
- Primary metric: simulated checkout conversion
- Guardrails: average order value and average delivery days
- Randomization diagnostic: chi-square sample ratio mismatch test
- Inference: two-sided two-proportion z-test and 95% confidence interval
- Decision rule: ship only when lift is positive and statistically significant, with no SRM

## Risks checked

1. Sample ratio mismatch
2. Missing or duplicate exposure IDs
3. Unequal pre-treatment covariate distributions
4. Peeking and repeated testing
5. Metric dilution and outliers
6. Guardrail deterioration

## Production enhancements

- Pre-register sample size and experiment duration.
- Randomize at user level when users can have repeated exposures.
- Add CUPED using a valid pre-period metric.
- Correct for multiple comparisons for secondary metrics.
- Use sequential testing only with an explicitly valid stopping rule.
