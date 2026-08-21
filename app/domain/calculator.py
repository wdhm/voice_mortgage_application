"""Deterministic borrowing-capacity calculator (the golden mortgage math).

Pure and side-effect free: given the case inputs it returns every intermediate
metric plus the outcome. The language model must never compute these numbers —
it only narrates the result this function produces.

Golden happy-path (Emma Lindberg), which the unit tests pin exactly:
    requested mortgage      5,250,000
    LTV                     75.0 %
    total debt              5,430,000
    annual gross income     1,152,000
    debt ratio              4.71x
    total amortization      13,125 / month  (2% + 1%)
    stressed net interest   21,437 / month  (7% gross - 30% tax)
    KALP surplus            5,138  / month  -> preliminary_positive
"""
from __future__ import annotations

from dataclasses import dataclass, field

from . import policy
from .models import CaseOutcome


def _round_half_up(value: float) -> int:
    """Deterministic half-up rounding to the nearest krona (no banker's rounding)."""
    return int(value + 0.5) if value >= 0 else -int(-value + 0.5)


@dataclass(frozen=True)
class CapacityInputs:
    property_price: int
    deposit: int
    gross_income_monthly: int
    net_income_monthly: int
    existing_debt_balance: int
    existing_debt_payment_monthly: int


@dataclass(frozen=True)
class CapacityComputation:
    inputs: dict
    metrics: dict
    outcome: CaseOutcome
    assumptions: list[str] = field(default_factory=lambda: list(policy.ASSUMPTIONS))
    caveats: list[str] = field(default_factory=lambda: list(policy.CAVEATS))


def compute_capacity(inp: CapacityInputs) -> CapacityComputation:
    m = policy.MONTHS_PER_YEAR

    requested_mortgage = inp.property_price - inp.deposit
    ltv = requested_mortgage / inp.property_price
    total_debt = requested_mortgage + inp.existing_debt_balance
    annual_gross_income = inp.gross_income_monthly * m
    debt_ratio = total_debt / annual_gross_income

    # Amortization (annual rate on the mortgage -> monthly krona).
    base_rate = policy.BASE_AMORT_RATE_HIGH_LTV if ltv > policy.LTV_HIGH_THRESHOLD else 0.0
    additional_rate = (
        policy.ADDITIONAL_AMORT_RATE if debt_ratio > policy.DEBT_RATIO_THRESHOLD else 0.0
    )
    base_amort_monthly = _round_half_up(requested_mortgage * base_rate / m)
    additional_amort_monthly = _round_half_up(requested_mortgage * additional_rate / m)
    total_amort_monthly = base_amort_monthly + additional_amort_monthly

    # Stressed interest with the illustrative tax adjustment.
    stressed_gross_interest_monthly = _round_half_up(
        requested_mortgage * policy.STRESSED_INTEREST_RATE / m
    )
    interest_tax_adjustment_monthly = _round_half_up(
        stressed_gross_interest_monthly * policy.INTEREST_TAX_ADJUSTMENT
    )
    stressed_net_interest_monthly = (
        stressed_gross_interest_monthly - interest_tax_adjustment_monthly
    )

    # KALP ("kvar att leva på") — surplus on NET income after all monthly costs.
    total_monthly_costs = (
        total_amort_monthly
        + stressed_net_interest_monthly
        + policy.LIVING_COST_MONTHLY
        + policy.PROPERTY_RUNNING_COST_MONTHLY
        + inp.existing_debt_payment_monthly
    )
    kalp_surplus_monthly = inp.net_income_monthly - total_monthly_costs

    outcome = (
        CaseOutcome.preliminary_positive
        if kalp_surplus_monthly > 0
        else CaseOutcome.preliminary_negative
    )

    metrics = {
        "requested_mortgage": requested_mortgage,
        "ltv": round(ltv, 4),
        "ltv_pct": round(ltv * 100, 1),
        "total_debt": total_debt,
        "annual_gross_income": annual_gross_income,
        "debt_ratio": round(debt_ratio, 2),
        "base_amort_monthly": base_amort_monthly,
        "additional_amort_monthly": additional_amort_monthly,
        "total_amort_monthly": total_amort_monthly,
        "stressed_gross_interest_monthly": stressed_gross_interest_monthly,
        "interest_tax_adjustment_monthly": interest_tax_adjustment_monthly,
        "stressed_net_interest_monthly": stressed_net_interest_monthly,
        "living_cost_monthly": policy.LIVING_COST_MONTHLY,
        "property_running_cost_monthly": policy.PROPERTY_RUNNING_COST_MONTHLY,
        "existing_debt_payment_monthly": inp.existing_debt_payment_monthly,
        "total_monthly_costs": total_monthly_costs,
        "kalp_surplus_monthly": kalp_surplus_monthly,
    }

    return CapacityComputation(
        inputs={
            "property_price": inp.property_price,
            "deposit": inp.deposit,
            "gross_income_monthly": inp.gross_income_monthly,
            "net_income_monthly": inp.net_income_monthly,
            "existing_debt_balance": inp.existing_debt_balance,
            "existing_debt_payment_monthly": inp.existing_debt_payment_monthly,
        },
        metrics=metrics,
        outcome=outcome,
    )
