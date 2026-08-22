"""Golden mortgage-calc: pin EVERY intermediate value (docs/functional-specification.md)."""
from __future__ import annotations

from app.domain.calculator import CapacityInputs, compute_capacity
from app.domain.models import CaseOutcome

EMMA = CapacityInputs(
    property_price=7_000_000,
    deposit=1_750_000,
    gross_income_monthly=96_000,
    net_income_monthly=62_400,
    existing_debt_balance=180_000,
    existing_debt_payment_monthly=4_200,
)


def test_golden_intermediate_metrics():
    m = compute_capacity(EMMA).metrics
    assert m["requested_mortgage"] == 5_250_000
    assert m["ltv_pct"] == 75.0
    assert m["total_debt"] == 5_430_000
    assert m["annual_gross_income"] == 1_152_000
    assert m["debt_ratio"] == 4.71
    assert m["base_amort_monthly"] == 8_750
    assert m["additional_amort_monthly"] == 4_375
    assert m["total_amort_monthly"] == 13_125
    assert m["stressed_gross_interest_monthly"] == 30_625
    assert m["interest_tax_adjustment_monthly"] == 9_188
    assert m["stressed_net_interest_monthly"] == 21_437
    assert m["living_cost_monthly"] == 12_500
    assert m["property_running_cost_monthly"] == 6_000
    assert m["existing_debt_payment_monthly"] == 4_200
    assert m["total_monthly_costs"] == 57_262


def test_golden_kalp_and_outcome():
    comp = compute_capacity(EMMA)
    assert comp.metrics["kalp_surplus_monthly"] == 5_138
    assert comp.outcome is CaseOutcome.preliminary_positive
    assert comp.metrics["amortization_tier"] == "2%"
    assert comp.metrics["stress_test_rate"] == 0.07
    assert comp.metrics["monthly_stressed_payment"] == 30_625
    assert comp.metrics["net_after_stress"] == 15_575
    assert comp.metrics["dti_ratio"] == 4.71
    assert comp.metrics["dti_flag"] == "above_soft_guideline"
    assert comp.metrics["verdict"] == "affordable_with_note"


def test_negative_surplus_flips_outcome():
    # Same debt but a much lower net income -> negative KALP.
    poor = CapacityInputs(
        property_price=7_000_000, deposit=1_750_000,
        gross_income_monthly=96_000, net_income_monthly=30_000,
        existing_debt_balance=180_000, existing_debt_payment_monthly=4_200,
    )
    comp = compute_capacity(poor)
    assert comp.metrics["kalp_surplus_monthly"] < 0
    assert comp.outcome is CaseOutcome.preliminary_negative


def test_calculation_is_pure_and_repeatable():
    a = compute_capacity(EMMA).metrics
    b = compute_capacity(EMMA).metrics
    assert a == b


def test_price_and_deposit_change_dti_and_clear_flag():
    lower_loan = CapacityInputs(
        property_price=4_000_000,
        deposit=2_000_000,
        gross_income_monthly=96_000,
        net_income_monthly=62_400,
        existing_debt_balance=180_000,
        existing_debt_payment_monthly=4_200,
    )

    result = compute_capacity(lower_loan).metrics

    assert result["requested_mortgage"] == 2_000_000
    assert result["dti_ratio"] == 1.89
    assert result["dti_flag"] == "within_guideline"
    assert result["verdict"] == "affordable"
